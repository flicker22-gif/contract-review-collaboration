"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import UploadZone from "@/components/UploadZone";
import { fetchDocuments, type DocumentListItem } from "@/lib/api";

export default function Home() {
  const [documents, setDocuments] = useState<DocumentListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchDocuments()
      .then(setDocuments)
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">合同审查协作工具</h1>
        <p className="mt-1 text-sm text-gray-500">
          上传合同 → 法务高亮风险条款并批注 → 业务逐条回复
        </p>
      </header>

      <UploadZone />

      <section className="mt-10">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">已上传的合同</h2>
        {loading && <p className="text-sm text-gray-400">加载中…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && documents.length === 0 && (
          <p className="text-sm text-gray-400">还没有合同，先上传一份吧。</p>
        )}
        <ul className="space-y-3">
          {documents.map((doc) => (
            <li key={doc.id}>
              <Link
                href={`/documents/${doc.id}`}
                className="flex items-center justify-between rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">
                    {doc.file_type === "pdf" ? "📕" : "📘"}
                  </span>
                  <div>
                    <p className="font-medium text-gray-900">{doc.filename}</p>
                    <p className="text-xs text-gray-400">
                      {new Date(doc.created_at).toLocaleString("zh-CN")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2 text-xs">
                  {doc.open_count > 0 && (
                    <span className="rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-700">
                      待处理 {doc.open_count}
                    </span>
                  )}
                  <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-600">
                    批注 {doc.annotation_count}
                  </span>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
