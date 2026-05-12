import { Message, Source } from "@/lib/types";
import MarkdownRenderer from "./MarkdownRenderer";
import SourceCard from "./SourceCard";

interface Props {
  message: Message;
  streamingContent?: string;
  streamingSources?: Source[];
  isStreaming?: boolean;
}

export default function MessageBubble({ message, streamingContent, streamingSources, isStreaming }: Props) {
  const isUser = message.role === "user";
  const content = isStreaming ? (streamingContent || "") : message.content;
  const sources = isStreaming ? (streamingSources || []) : message.sources;

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[80%] rounded-lg px-4 py-3 ${
        isUser ? "bg-red-700 text-white" : "bg-gray-100 text-gray-800"
      }`}>
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{content}</p>
        ) : (
          <>
            <MarkdownRenderer content={content} />
            {isStreaming && !content && <span className="inline-block w-2 h-4 bg-gray-400 animate-pulse" />}
            <SourceCard sources={sources} />
          </>
        )}
      </div>
    </div>
  );
}
