"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  createAnnotation,
  createReply,
  deleteAnnotation,
  fetchAnnotations,
  fetchDocument,
  updateAnnotationStatus,
  type Annotation,
  type DocumentDetail,
} from "@/lib/api";
import { useIdentity } from "@/lib/identity";
import DocumentViewer, { type SelectionInfo } from "@/components/DocumentViewer";
import AnnotationPanel from "@/components/AnnotationPanel";

export default function DocumentReviewPage({
  params,
}: {
  params: { id: string };
}) {
  const documentId = Number(params.id);
  const [document, setDocument] = useState<DocumentDetail | null>(null);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [identity, setIdentity] = useIdentity();

  const highlightRefs = useRef(new Map<number, HTMLElement>());
  const cardRefs = useRef(new Map<number, HTMLElement>());

  useEffect(() => {
    Promise.all([fetchDocument(documentId), fetchAnnotations(documentId)])
      .then(([doc, anns]) => {
        setDocument(doc);
        setAnnotations(anns);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "加载失败"));
  }, [documentId]);

  /** 点击任一侧（高亮/卡片）时，另一侧滚动定位 */
  const selectAnnotation = useCallback(
    (id: number, source: "viewer" | "panel") => {
      setSelectedId(id);
      const target =
        source === "viewer" ? cardRefs.current.get(id) : highlightRefs.current.get(id);
      if (target) {
        target.scrollIntoView({ behavior: "smooth", block: "center" });
        if (source === "panel") {
          target.classList.remove("highlight-flash");
          void target.offsetWidth; // 重新触发动画
          target.classList.add("highlight-flash");
        }
      }
    },
    []
  );

  const handleCreateAnnotation = async (sel: SelectionInfo, comment: string) => {
    const created = await createAnnotation(documentId, {
      paragraph_id: sel.paragraphId,
      start_offset: sel.startOffset,
      end_offset: sel.endOffset,
      comment,
      author_name: identity.name,
      author_role: identity.role,
    });
    setAnnotations((prev) => [...prev, created]);
  };

  const handleReply = async (annotationId: number, content: string) => {
    const reply = await createReply(annotationId, {
      author_name: identity.name,
      author_role: identity.role,
      content,
    });
    setAnnotations((prev) =>
      prev.map((a) =>
        a.id === annotationId ? { ...a, replies: [...a.replies, reply] } : a
      )
    );
  };

  const handleToggleStatus = async (annotation: Annotation) => {
    const updated = await updateAnnotationStatus(
      annotation.id,
      annotation.status === "open" ? "resolved" : "open"
    );
    setAnnotations((prev) =>
      prev.map((a) => (a.id === updated.id ? { ...a, ...updated } : a))
    );
  };

  const handleDelete = async (annotationId: number) => {
    await deleteAnnotation(annotationId);
    setAnnotations((prev) => prev.filter((a) => a.id !== annotationId));
    if (selectedId === annotationId) setSelectedId(null);
  };

  if (error) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10">
        <p className="text-red-600">加载失败：{error}</p>
        <Link href="/" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
          ← 返回列表
        </Link>
      </main>
    );
  }

  if (!document) {
    return <main className="mx-auto max-w-4xl px-6 py-10 text-gray-400">加载中…</main>;
  }

  return (
    <main className="mx-auto flex h-screen max-w-7xl flex-col px-6 py-4">
      {/* 顶栏：返回 + 文件名 + 身份信息 */}
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            ← 返回
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">
            {document.filename}
          </h1>
          <span className="rounded bg-gray-100 px-2 py-0.5 text-xs uppercase text-gray-500">
            {document.file_type}
          </span>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-500">我是：</span>
          <input
            value={identity.name}
            onChange={(e) => setIdentity({ ...identity, name: e.target.value })}
            placeholder="姓名"
            className="w-24 rounded-lg border border-gray-300 px-2 py-1 outline-none focus:border-blue-500"
          />
          <select
            value={identity.role}
            onChange={(e) =>
              setIdentity({ ...identity, role: e.target.value as "legal" | "business" })
            }
            className="rounded-lg border border-gray-300 px-2 py-1 outline-none focus:border-blue-500"
          >
            <option value="legal">法务</option>
            <option value="business">业务</option>
          </select>
        </div>
      </header>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-6 pb-4 lg:grid-cols-[1fr_380px]">
        {/* 左：文档 */}
        <div className="min-h-0 overflow-y-auto">
          <DocumentViewer
            paragraphs={document.paragraphs}
            annotations={annotations}
            selectedAnnotationId={selectedId}
            canAnnotate={identity.name.trim().length > 0}
            onSelectAnnotation={(id) => selectAnnotation(id, "viewer")}
            onCreateAnnotation={handleCreateAnnotation}
            registerHighlightRef={(id, el) => {
              if (el) highlightRefs.current.set(id, el);
              else highlightRefs.current.delete(id);
            }}
          />
        </div>

        {/* 右：批注面板 */}
        <div className="min-h-0">
          <AnnotationPanel
            annotations={annotations}
            paragraphs={document.paragraphs}
            selectedAnnotationId={selectedId}
            identity={identity}
            onSelectAnnotation={(id) => selectAnnotation(id, "panel")}
            onReply={handleReply}
            onToggleStatus={handleToggleStatus}
            onDelete={handleDelete}
            registerCardRef={(id, el) => {
              if (el) cardRefs.current.set(id, el);
              else cardRefs.current.delete(id);
            }}
          />
        </div>
      </div>
    </main>
  );
}
