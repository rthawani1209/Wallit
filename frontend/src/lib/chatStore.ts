import type { ChatMessage } from "./api";

// Module-scoped (not component state) so the conversation survives navigating
// to another tab and back — Next.js client-side routing unmounts the page
// component, but this module stays loaded. A real page refresh reloads the
// module and clears it, which is the intended reset point.
let messages: ChatMessage[] = [];

export function getStoredMessages(): ChatMessage[] {
  return messages;
}

export function setStoredMessages(next: ChatMessage[]) {
  messages = next;
}
