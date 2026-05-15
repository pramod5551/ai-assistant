/** Outbound payload — field names match BFF Jackson `@JsonProperty` (snake_case). */
export type AssistChatRequest = {
  message: string;
  session_id?: string;
  structured_output?: boolean;
};

export type AssistCitation = {
  document_id: string;
  title: string;
  library_id: string;
  snippet: string;
};

export type AssistChatResponse = {
  correlation_id: string;
  answer_text: string;
  structured: Record<string, unknown> | null;
  citations: AssistCitation[] | null;
  graph_path: string;
};
