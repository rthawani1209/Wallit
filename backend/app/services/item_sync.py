"""Syncing one linked bank (a PlaidItem) into the database.

The first sync pulls the bank's whole history and saves Plaid's cursor. Every
later sync sends that cursor and gets back only what changed since, so a
resync or the nightly job costs one quick request instead of a full re-pull."""
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.category import Category
from app.models.plaid_item import PlaidItem
from app.services import encryption, plaid as plaid_service
from app.services.transaction_sync import prune_missing_transactions, remove_transactions, save_transactions

HISTORY_COMPLETE = "HISTORICAL_UPDATE_COMPLETE"
# Right after linking, Plaid may still be pulling the history, so the first sync
# polls a few times. Anything not ready by then arrives on the next sync.
FIRST_SYNC_POLLS = 5
POLL_SECONDS = 2


def _pull(access_token: str, cursor: str | None) -> tuple[list[dict], list[str], str, bool]:
    """Changes since `cursor` as (upserts, removed_ids, next_cursor, history_complete),
    deduplicated so a transaction added then modified or removed shows up once."""
    upserts, removed, cursor_out, status = plaid_service.sync_transactions(access_token, cursor)
    if cursor is None:
        for _ in range(FIRST_SYNC_POLLS):
            if status == HISTORY_COMPLETE:
                break
            time.sleep(POLL_SECONDS)
            more, more_removed, cursor_out, status = plaid_service.sync_transactions(access_token, cursor_out)
            upserts.extend(more)
            removed.extend(more_removed)

    removed_set = set(removed)
    latest = {t["plaid_transaction_id"]: t for t in upserts if t["plaid_transaction_id"] not in removed_set}
    return list(latest.values()), list(removed_set), cursor_out, status == HISTORY_COMPLETE


def _backfill_item_id(db: Session, item: PlaidItem, access_token: str) -> bool:
    """Banks linked before plaid_items existed have no item_id, so re-linking
    them couldn't find their row. Look it up once. Returns False if the user has
    since re-linked the same login under a new row, in which case this one is a
    stale duplicate and is deleted (its accounts fall back to the newer row on
    that row's next sync)."""
    item_id = plaid_service.get_item_id(access_token)
    duplicate = (
        db.query(PlaidItem)
        .filter(PlaidItem.item_id == item_id, PlaidItem.id != item.id)
        .first()
    )
    if duplicate is not None:
        db.query(Account).filter(Account.plaid_item_id == item.id).update({Account.plaid_item_id: duplicate.id})
        db.delete(item)
        db.commit()
        return False
    item.item_id = item_id
    return True


def sync_item(db: Session, item: PlaidItem) -> int:
    """Apply this bank's changes since its last sync. Returns rows touched."""
    access_token = encryption.decrypt(item.access_token)
    if item.item_id is None and not _backfill_item_id(db, item, access_token):
        return 0
    accounts = db.query(Account).filter(Account.plaid_item_id == item.id).all()
    account_map = {a.plaid_account_id: a.id for a in accounts}
    category_map = {c.name: c.id for c in db.query(Category).all()}

    full_pull = item.cursor is None
    upserts, removed, next_cursor, history_complete = _pull(access_token, item.cursor)

    touched = save_transactions(db, account_map, category_map, upserts)
    db.flush()
    touched += remove_transactions(db, list(account_map.values()), removed)

    # Only a full pull lists every transaction the bank has, so only then can a
    # row we hold but Plaid didn't send be called stale (usually a pending charge
    # saved before removals were handled). Incremental syncs report removals
    # explicitly. prune_missing_transactions has its own guards on top of this.
    if full_pull:
        synced = {account_map[t["plaid_account_id"]] for t in upserts if t["plaid_account_id"] in account_map}
        touched += prune_missing_transactions(
            db, list(synced), {t["plaid_transaction_id"] for t in upserts}, history_complete
        )

    item.cursor = next_cursor
    item.last_synced_at = datetime.now(timezone.utc)
    db.commit()
    return touched
