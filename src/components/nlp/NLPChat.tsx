import { useState, useRef, useEffect } from "react";
import { api } from "../../services/api";

interface ChatMessage {
  id: string;
  role: "user" | "system";
  text: string;
  timestamp: Date;
  actions?: Array<{
    action: string;
    target?: string;
    details?: Record<string, unknown>;
  }>;
  error?: boolean;
}

const SUGGESTIONS = [
  "Add a filter where temperature > 40",
  "Scale the window operator to 3 instances",
  "Remove the console sink",
  "Add an alert sink after the filter",
  "Show me the current pipeline",
];

interface NLPChatProps {
  pipelineId: string | null;
}

export function NLPChat({ pipelineId }: NLPChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "system",
      text: "I can modify your pipeline using natural language. Try commands like \"add a filter where temperature > 40\" or \"scale the window to 3 instances\".",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendCommand = async (text: string) => {
    if (!text.trim() || !pipelineId) return;

    const userMsg: ChatMessage = {
      id: `msg-${Date.now()}`,
      role: "user",
      text: text.trim(),
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const result = (await api.sendNLPCommand(pipelineId, text.trim())) as {
        actions_applied: number;
        actions: Array<{
          action: string;
          target?: string;
          details?: Record<string, unknown>;
        }>;
        message: string;
      };

      const sysMsg: ChatMessage = {
        id: `msg-${Date.now()}-resp`,
        role: "system",
        text:
          result.message ||
          `Applied ${result.actions_applied} action(s) to the pipeline.`,
        timestamp: new Date(),
        actions: result.actions,
      };
      setMessages((prev) => [...prev, sysMsg]);
    } catch (e) {
      const errMsg: ChatMessage = {
        id: `msg-${Date.now()}-err`,
        role: "system",
        text:
          e instanceof Error ? e.message : "Failed to process command",
        timestamp: new Date(),
        error: true,
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendCommand(input);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-flowstorm-surface border-b border-flowstorm-border px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-lg">&#128172;</span>
          <h2 className="text-sm font-bold text-flowstorm-text">
            Natural Language Pipeline Editor
          </h2>
        </div>
        <p className="text-[10px] text-flowstorm-muted mt-0.5">
          Modify your pipeline using plain English commands
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${
              msg.role === "user" ? "justify-end" : "justify-start"
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-3 py-2 ${
                msg.role === "user"
                  ? "bg-flowstorm-primary/20 border border-flowstorm-primary/30"
                  : msg.error
                  ? "bg-red-500/10 border border-red-500/30"
                  : "bg-flowstorm-bg border border-flowstorm-border"
              }`}
            >
              <p
                className={`text-xs ${
                  msg.error
                    ? "text-red-400"
                    : "text-flowstorm-text"
                }`}
              >
                {msg.text}
              </p>

              {msg.actions && msg.actions.length > 0 && (
                <div className="mt-2 space-y-1">
                  {msg.actions.map((action, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-1.5 text-[10px]"
                    >
                      <span className="text-flowstorm-success">&#10003;</span>
                      <span className="text-flowstorm-muted">
                        {action.action}
                        {action.target ? ` on ${action.target}` : ""}
                      </span>
                    </div>
                  ))}
                </div>
              )}

              <div className="text-[10px] text-flowstorm-muted mt-1">
                {msg.timestamp.toLocaleTimeString()}
              </div>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-flowstorm-bg border border-flowstorm-border rounded-lg px-3 py-2">
              <div className="flex gap-1">
                <div className="w-1.5 h-1.5 rounded-full bg-flowstorm-primary animate-bounce" />
                <div
                  className="w-1.5 h-1.5 rounded-full bg-flowstorm-primary animate-bounce"
                  style={{ animationDelay: "0.15s" }}
                />
                <div
                  className="w-1.5 h-1.5 rounded-full bg-flowstorm-primary animate-bounce"
                  style={{ animationDelay: "0.3s" }}
                />
              </div>
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* Suggestions */}
      {!pipelineId ? (
        <div className="px-4 py-3 bg-flowstorm-surface border-t border-flowstorm-border">
          <p className="text-xs text-flowstorm-muted text-center">
            Deploy a pipeline to start using NLP commands
          </p>
        </div>
      ) : (
        <>
          <div className="px-4 py-2 flex gap-2 overflow-x-auto">
            {SUGGESTIONS.map((s) => (
              <button
                key={s}
                onClick={() => sendCommand(s)}
                disabled={loading}
                className="flex-shrink-0 text-[10px] px-2.5 py-1 rounded-full
                  border border-flowstorm-border text-flowstorm-muted
                  hover:border-flowstorm-primary hover:text-flowstorm-primary
                  transition-colors disabled:opacity-50"
              >
                {s}
              </button>
            ))}
          </div>

          {/* Input */}
          <form
            onSubmit={handleSubmit}
            className="flex gap-2 px-4 py-3 bg-flowstorm-surface border-t border-flowstorm-border"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a command..."
              disabled={loading}
              className="flex-1 bg-flowstorm-bg border border-flowstorm-border rounded-md px-3 py-2
                text-xs text-flowstorm-text placeholder-flowstorm-muted
                focus:outline-none focus:border-flowstorm-primary transition-colors"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2 rounded-md bg-flowstorm-primary hover:bg-flowstorm-primary/80
                text-white text-xs font-bold transition-colors disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </>
      )}
    </div>
  );
}
