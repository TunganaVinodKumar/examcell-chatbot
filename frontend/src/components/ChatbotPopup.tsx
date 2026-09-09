import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, Send, User, FileText, Sparkles } from "lucide-react";
import botImage from "../assets/R.jpg";

const DEFAULT_API_BASE =
  import.meta.env.VITE_API_BASE || "https://examcell-chatbot.onrender.com";

interface ChatbotPopupProps {
  chatbotUrl?: string;
}

type SourceInfo = {
  doc_id?: string;
  filename?: string;
  url?: string;
  snippet?: string;
  confidence?: number;
  semester?: number;
  exam_type?: string;
};

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  source?: SourceInfo;
  sources?: SourceInfo[];
};

const normalizeAssistantText = (text: string) => {
  if (!text) return "";
  return text.replace(/\*\*/g, "").trim();
};

const normalizeSource = (source: SourceInfo): SourceInfo => ({
  doc_id: source.doc_id,
  filename: source.filename,
  url: source.url,
  snippet: source.snippet,
  confidence: source.confidence,
  semester: source.semester,
  exam_type: source.exam_type,
});

const dedupeSources = (sources: SourceInfo[]) => {
  const seen = new Set<string>();
  const result: SourceInfo[] = [];

  for (const source of sources) {
    const key = `${source.doc_id || ""}::${source.filename || ""}::${source.url || ""}`;
    if (!source.filename || !source.url || seen.has(key)) {
      continue;
    }
    seen.add(key);
    result.push(source);
  }

  return result;
};

const ChatbotPopup = ({ chatbotUrl }: ChatbotPopupProps) => {
  const apiBase = chatbotUrl?.trim() || DEFAULT_API_BASE;

  const [isOpen, setIsOpen] = useState(true);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      content:
        "Hello! Welcome to the NSRIT Exam Cell. I am Cella. Ask me about sem timetables, mid timetables, supply fees, revaluation fees, sem fees, and exam circulars.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const openChat = () => {
    setIsOpen(true);
  };

  const closeChat = () => {
    setIsOpen(false);
  };

  const sendMessage = async () => {
    const outgoingText = input.trim();

    if (!outgoingText || loading) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: outgoingText,
    };

    const nextMessages = [...messages, userMessage];

    setMessages(nextMessages);
    setInput("");
    setLoading(true);

    try {
      const historyPayload = nextMessages.slice(0, -1).map((msg) => ({
        role: msg.role,
        content: msg.content,
      }));

      const res = await fetch(`${apiBase}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          prompt: outgoingText,
          history: historyPayload,
        }),
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || data?.answer || "Unable to fetch response");
      }

      if (!data?.answer) {
        throw new Error("Empty response");
      }

      const normalizedSources = dedupeSources(
        [
          ...(data.source ? [normalizeSource(data.source)] : []),
          ...(Array.isArray(data.sources)
            ? data.sources.map((source: SourceInfo) => normalizeSource(source))
            : []),
        ]
      );

      const botMessage: ChatMessage = {
        role: "assistant",
        content: normalizeAssistantText(data.answer),
        source: normalizedSources[0],
        sources: normalizedSources.length > 0 ? normalizedSources : undefined,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : "Unable to fetch response right now. Please try again or check whether the backend server is running.";

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Unable to get a response right now. ${errorMessage}`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const renderDocumentButtons = (msg: ChatMessage) => {
    const allSources = dedupeSources(
      msg.sources && msg.sources.length > 0
        ? msg.sources
        : msg.source
          ? [msg.source]
          : []
    );

    if (allSources.length === 0) {
      return null;
    }

    return (
      <div className="mt-3 flex flex-wrap gap-2">
        {allSources.map((source, index) => (
          <button
            key={`${source.doc_id || source.filename || "source"}-${index}`}
            onClick={() => window.open(source.url, "_blank", "noopener,noreferrer")}
            title={source.filename}
            className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
          >
            <FileText className="h-4 w-4" />
            {allSources.length === 1 ? "Open Document" : `Open Document ${index + 1}`}
          </button>
        ))}
      </div>
    );
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 20 }}
            transition={{ type: "spring", stiffness: 280, damping: 24 }}
            className="absolute bottom-20 right-0 flex h-[580px] w-[390px] flex-col overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-2xl"
          >
            <div className="bg-gradient-to-r from-slate-900 via-blue-900 to-slate-800 px-4 py-4 text-white">
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-11 w-11 overflow-hidden rounded-full border border-white/20 bg-white/10">
                    <img
                      src={botImage}
                      alt="Exam Cell Assistant"
                      className="h-full w-full object-cover"
                    />
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold">
                      NSRIT Exam Cell Assistant
                    </h3>
                    <div className="mt-1 flex items-center gap-1 text-[11px] text-emerald-300">
                      <Sparkles className="h-3 w-3" />
                      Online for student queries
                    </div>
                  </div>
                </div>

                <button
                  onClick={closeChat}
                  className="rounded-full p-1 text-white/75 transition hover:bg-white/10 hover:text-white"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            <div className="flex flex-1 flex-col overflow-hidden bg-gradient-to-b from-slate-50 to-white">
              <div className="flex-1 overflow-y-auto p-4">
                <div className="space-y-4">
                  {messages.map((msg, index) => (
                    <div
                      key={index}
                      className={`flex items-end gap-2 ${
                        msg.role === "user" ? "justify-end" : "justify-start"
                      }`}
                    >
                      {msg.role === "assistant" && (
                        <div className="h-8 w-8 shrink-0 overflow-hidden rounded-full border border-slate-200 bg-white">
                          <img
                            src={botImage}
                            alt="Assistant"
                            className="h-full w-full object-cover"
                          />
                        </div>
                      )}

                      <div
                        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                          msg.role === "user"
                            ? "rounded-br-md bg-slate-900 text-white"
                            : "rounded-bl-md border border-slate-200 bg-white text-slate-800"
                        }`}
                      >
                        <div className="whitespace-pre-line leading-6">
                          {msg.content}
                        </div>

                        {msg.role === "assistant" && renderDocumentButtons(msg)}
                      </div>

                      {msg.role === "user" && (
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-100">
                          <User className="h-4 w-4 text-blue-700" />
                        </div>
                      )}
                    </div>
                  ))}

                  {loading && (
                    <div className="flex items-end gap-2">
                      <div className="h-8 w-8 shrink-0 overflow-hidden rounded-full border border-slate-200 bg-white">
                        <img
                          src={botImage}
                          alt="Assistant"
                          className="h-full w-full object-cover"
                        />
                      </div>

                      <div className="rounded-2xl rounded-bl-md border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm">
                        Cella is checking the exam cell documents...
                      </div>
                    </div>
                  )}

                  <div ref={messagesEndRef} />
                </div>
              </div>

              <div className="border-t border-slate-200 bg-white p-3">
                <div className="flex items-end gap-2">
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !loading) {
                        e.preventDefault();
                        sendMessage();
                      }
                    }}
                    placeholder="Ask about sem timetable, mid timetable, supply fees..."
                    className="flex-1 rounded-full border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition focus:border-slate-400 focus:bg-white"
                  />

                  <button
                    onClick={sendMessage}
                    disabled={loading || !input.trim()}
                    className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-900 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </div>

                <p className="mt-2 text-[11px] text-slate-500">
                  Ask specific questions like semester, exam type, fee type, or circular name.
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {!isOpen && (
        <motion.button
          onClick={openChat}
          initial={{ opacity: 0, x: 10, y: 10 }}
          animate={{ opacity: 1, x: 0, y: 0 }}
          exit={{ opacity: 0, x: 10, y: 10 }}
          className="absolute bottom-16 right-2 flex max-w-[250px] items-center gap-2 rounded-full border border-slate-200 bg-white px-4 py-2 text-slate-800 shadow-lg"
        >
          <img
            src={botImage}
            alt="Exam Cell Assistant"
            className="h-8 w-8 rounded-full object-cover"
          />
          <span className="truncate text-sm font-medium">
            Hi! I&apos;m Cella, ask exam cell queries
          </span>
        </motion.button>
      )}

      <motion.button
        onClick={() => {
          if (isOpen) {
            closeChat();
          } else {
            openChat();
          }
        }}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.95 }}
        className="flex h-14 w-14 items-center justify-center overflow-hidden rounded-full border border-slate-200 bg-white shadow-xl transition-all hover:brightness-110 animate-bounce"
      >
        <AnimatePresence mode="wait">
          {isOpen ? (
            <motion.div
              key="close"
              initial={{ rotate: -90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: 90, opacity: 0 }}
            >
              <X className="h-6 w-6 text-slate-700" />
            </motion.div>
          ) : (
            <motion.div
              key="chat-image"
              initial={{ rotate: 90, opacity: 0 }}
              animate={{ rotate: 0, opacity: 1 }}
              exit={{ rotate: -90, opacity: 0 }}
              className="h-full w-full"
            >
              <img
                src={botImage}
                alt="Chatbot"
                className="h-full w-full object-cover"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </motion.button>
    </div>
  );
};

export default ChatbotPopup;
