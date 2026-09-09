import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FileText,
  Database,
  Upload,
  Trash2,
  LogOut,
  ScanText,
} from "lucide-react";
import Header from "@/components/Header";

const API_BASE =
  import.meta.env.VITE_API_BASE || "https://examcell-chatbot.onrender.com";

type Chunk = {
  chunk_index: number;
  text: string;
};

type UploadedDocument = {
  filename: string;
  doc_id: string;
  chunks: Chunk[];
};

const ExamcellDashboard = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const [stats, setStats] = useState({ documents: 0, chunks: 0 });
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [dpi, setDpi] = useState(300);
  const [forceOCR, setForceOCR] = useState(false);
  const [uploadedDocs, setUploadedDocs] = useState<UploadedDocument[]>([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const loggedIn = localStorage.getItem("examcellLoggedIn");

    if (!loggedIn) {
      navigate("/examcell-login");
      return;
    }

    fetchStats();
  }, [navigate]);

  const fetchStats = async () => {
    try {
      setError("");
      const res = await fetch(`${API_BASE}/examcell/stats`);
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || "Failed to fetch dashboard stats");
      }

      setStats({
        documents: data?.documents || 0,
        chunks: data?.chunks || 0,
      });
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch dashboard stats"
      );
    } finally {
      setLoading(false);
    }
  };

  const resetFileSelection = () => {
    setSelectedFiles([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      setError("Please select files first.");
      return;
    }

    setUploadedDocs([]);
    setUploading(true);
    setError("");
    setNotice("");

    try {
      const formData = new FormData();

      selectedFiles.forEach((file) => {
        formData.append("files", file);
      });

      formData.append("dpi", dpi.toString());
      formData.append("force_ocr", forceOCR.toString());

      const res = await fetch(`${API_BASE}/examcell/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || "Upload failed");
      }

      if (!data?.success || !Array.isArray(data?.documents)) {
        throw new Error("Upload failed");
      }

      const docs: UploadedDocument[] = await Promise.all(
        data.documents
          .filter((doc: { filename: string; doc_id?: string }) => doc.doc_id)
          .map(async (doc: { filename: string; doc_id: string }) => {
            try {
              const resChunks = await fetch(
                `${API_BASE}/examcell/document/${doc.doc_id}`
              );
              const chunkData = await resChunks.json().catch(() => null);

              if (!resChunks.ok) {
                throw new Error("Failed to fetch chunks");
              }

              return {
                filename: doc.filename,
                doc_id: doc.doc_id,
                chunks: Array.isArray(chunkData?.chunks) ? chunkData.chunks : [],
              };
            } catch {
              return {
                filename: doc.filename,
                doc_id: doc.doc_id,
                chunks: [],
              };
            }
          })
      );

      setUploadedDocs(docs);
      resetFileSelection();
      setNotice(
        `${docs.length} document${docs.length === 1 ? "" : "s"} uploaded successfully.`
      );
      fetchStats();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  const handleClear = async () => {
    const confirmed = window.confirm(
      "Are you sure you want to clear the knowledge base?"
    );

    if (!confirmed) return;

    setClearing(true);
    setError("");
    setNotice("");

    try {
      const res = await fetch(`${API_BASE}/examcell/clear`, {
        method: "POST",
      });

      const data = await res.json().catch(() => null);

      if (!res.ok) {
        throw new Error(data?.detail || "Failed to clear knowledge base");
      }

      setUploadedDocs([]);
      resetFileSelection();
      setNotice("Knowledge base cleared successfully.");
      fetchStats();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to clear knowledge base"
      );
    } finally {
      setClearing(false);
    }
  };

  const handleLogout = async () => {
    try {
      await fetch(`${API_BASE}/examcell/logout`, {
        method: "POST",
      });
    } catch (err) {
      console.error("Logout request failed", err);
    } finally {
      localStorage.removeItem("examcellLoggedIn");
      navigate("/examcell-login");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100">
      <Header />

      <main className="px-4 py-10 md:py-12">
        <div className="container mx-auto max-w-5xl">
          <div className="mb-8 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">
                Admin Workspace
              </p>
              <h1 className="mt-2 font-display text-3xl font-bold text-primary md:text-4xl">
                Exam Cell Dashboard
              </h1>
              <p className="mt-2 text-sm text-slate-600">
                Manage uploads, OCR settings, and chunk previews from one place.
              </p>
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleClear}
                disabled={clearing || uploading}
                className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-4 py-2.5 text-sm font-medium text-red-700 transition hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-60"
              >
                <Trash2 className="h-4 w-4" />
                {clearing ? "Clearing..." : "Clear Knowledge Base"}
              </button>

              <button
                onClick={handleLogout}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2.5 text-sm font-medium text-white transition hover:bg-slate-800"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {notice && (
            <div className="mb-6 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              {notice}
            </div>
          )}

          {loading ? (
            <div className="mb-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
              <p className="text-sm text-slate-600">Loading dashboard stats...</p>
            </div>
          ) : (
            <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-2">
              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-primary">
                  <FileText className="h-6 w-6" />
                </div>
                <h2 className="text-sm font-medium text-slate-500">Documents</h2>
                <p className="mt-2 text-3xl font-bold text-slate-900">
                  {stats.documents}
                </p>
              </div>

              <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-amber-700">
                  <Database className="h-6 w-6" />
                </div>
                <h2 className="text-sm font-medium text-slate-500">Chunks</h2>
                <p className="mt-2 text-3xl font-bold text-slate-900">
                  {stats.chunks}
                </p>
              </div>
            </div>
          )}

          <div className="mb-8 rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:p-8">
            <div className="mb-6 flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-white">
                <Upload className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-xl font-semibold text-slate-900">
                  Upload Documents
                </h2>
                <p className="text-sm text-slate-600">
                  Supports scanned PDFs, typed PDFs, and DOCX files.
                </p>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-[180px_1fr]">
              <div className="space-y-5">
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-700">
                    OCR DPI
                  </label>
                  <input
                    type="number"
                    value={dpi}
                    min={150}
                    max={600}
                    step={50}
                    onChange={(e) => setDpi(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-slate-900 outline-none transition focus:border-primary focus:bg-white focus:ring-2 focus:ring-primary/20"
                  />
                </div>

                <label className="flex items-center gap-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <input
                    id="force-ocr"
                    type="checkbox"
                    checked={forceOCR}
                    onChange={(e) => setForceOCR(e.target.checked)}
                    className="h-4 w-4"
                  />
                  <div className="flex items-center gap-2 text-sm font-medium text-slate-700">
                    <ScanText className="h-4 w-4" />
                    Force OCR
                  </div>
                </label>
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Select Files
                </label>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx"
                  multiple
                  onChange={(e) => {
                    if (e.target.files) {
                      setSelectedFiles(Array.from(e.target.files));
                    }
                  }}
                  className="block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700 file:mr-4 file:rounded-lg file:border-0 file:bg-slate-900 file:px-4 file:py-2 file:text-sm file:font-medium file:text-white hover:file:bg-slate-800"
                />

                {selectedFiles.length > 0 && (
                  <div className="mt-4 rounded-2xl bg-slate-50 p-4 text-sm text-slate-700">
                    <p className="mb-2 font-medium text-slate-900">
                      Selected files
                    </p>
                    <div className="space-y-2">
                      {selectedFiles.map((file) => (
                        <div key={file.name} className="truncate">
                          {file.name}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="mt-5 flex flex-wrap gap-3">
                  <button
                    onClick={handleUpload}
                    disabled={uploading}
                    className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-70"
                  >
                    {uploading && (
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    )}
                    {uploading ? "Processing..." : "Upload Document"}
                  </button>

                  <button
                    onClick={resetFileSelection}
                    type="button"
                    className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                  >
                    Reset Selection
                  </button>
                </div>
              </div>
            </div>
          </div>

          {uploadedDocs.length > 0 && (
            <div className="space-y-8">
              {uploadedDocs.map((doc) => (
                <div
                  key={doc.doc_id}
                  className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm md:p-8"
                >
                  <h2 className="mb-2 text-xl font-semibold text-slate-900">
                    {doc.filename}
                  </h2>

                  <p className="mb-5 text-sm text-slate-500">
                    Document ID: {doc.doc_id}
                  </p>

                  {doc.chunks.length === 0 ? (
                    <div className="rounded-2xl border border-yellow-200 bg-yellow-50 p-4 text-sm text-yellow-800">
                      No chunks available for preview.
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {doc.chunks.map((chunk) => (
                        <div key={`${doc.doc_id}-${chunk.chunk_index}`}>
                          <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-700">
                            Chunk {chunk.chunk_index}
                          </h3>

                          <pre className="overflow-x-auto rounded-2xl bg-slate-50 p-4 text-sm whitespace-pre-wrap text-slate-800">
                            {chunk.text}
                          </pre>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default ExamcellDashboard;
