import type { ChatMessage } from "./api";

// module-scoped so the chat survives switching tabs, but a real refresh still clears it
let messages: ChatMessage[] = [];

export function getStoredMessages(): ChatMessage[] {
  return messages;
}

export function setStoredMessages(next: ChatMessage[]) {
  messages = next;
}
