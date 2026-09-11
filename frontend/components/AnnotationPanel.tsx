"use client";

import { useMemo, useState } from "react";
import type { Annotation, Paragraph } from "@/lib/api";
import type { Identity } from "@/lib/identity";
import AnnotationCard from "./AnnotationCard";

type Filter = "all" | "open" | "resolved";

const FILTER_TABS: { key: Filter; label: string }[] = [
  { key: "all", label: "全部" },
  { key: "open", label: "待处理" },
  { key: "resolved", label: "已解决" },
];

interface AnnotationPanelProps {
  annotations: Annotation[];
  paragraphs: Paragraph[];
  selectedAnnotationId: number | null;
  identity: Identity;
  onSelectAnnotation: (id: number) => void;
  onReply: (annotationId: number, content: string) => Promise<void>;
  onToggleStatus: (annotation: Annotation) => Promise<void>;
  onDelete: (annotationId: number) => Promise<void>;
  registerCardRef: (annotationId: number, el: HTMLElement | null) => void;
}

export default function AnnotationPanel({
  annotations,
  paragraphs,
  selectedAnnotationId,
  identity,
  onSelectAnnotation,
  onReply,
  onToggleStatus,
  onDelete,
  registerCardRef,
}: AnnotationPanelProps) {
  const [filter, setFilter] = useState<Filter>("all");

  const paragraphIdxById = useMemo(() => {
    const map = new Map<number, number>();
    for (const p of paragraphs) map.set(p.id, p.idx);
    return map;
  }, [paragraphs]);

  const sorted = useMemo(() => {
    const filtered = annotations.filter(
      (a) => filter === "all" || a.status === filter
    );
    return [...filtered].sort((a, b) => {
      const ia = paragraphIdxById.get(a.paragraph_id) ?? 0;
      const ib = paragraphIdxById.get(b.paragraph_id) ?? 0;
      return ia - ib || a.start_offset - b.start_offset;
    });
  }, [annotations, filter, paragraphIdxById]);

  const counts = useMemo(
    () => ({
      all: annotations.length,
      open: annotations.filter((a) => a.status === "open").length,
      resolved: annotations.filter((a) => a.status === "resolved").length,
    }),
    [annotations]
  );

  return (
    <div className="flex h-full flex-col">
      <div className="mb-3 flex items-center gap-1 rounded-lg bg-gray-100 p-1">
        {FILTER_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`flex-1 rounded-md px-2 py-1.5 text-xs font-medium transition-colors ${
              filter === tab.key
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label}（{counts[tab.key]}）
          </button>
        ))}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
        {sorted.length === 0 && (
          <p className="py-8 text-center text-sm text-gray-400">
            {filter === "all"
              ? "还没有批注。在左侧文档中划选文字即可添加。"
              : "该状态下暂无批注。"}
          </p>
        )}
        {sorted.map((a) => (
          <AnnotationCard
            key={a.id}
            annotation={a}
            paragraphIdx={paragraphIdxById.get(a.paragraph_id)}
            selected={a.id === selectedAnnotationId}
            identity={identity}
            onSelect={() => onSelectAnnotation(a.id)}
            onReply={(content) => onReply(a.id, content)}
            onToggleStatus={() => onToggleStatus(a)}
            onDelete={() => onDelete(a.id)}
            cardRef={(el) => registerCardRef(a.id, el)}
          />
        ))}
      </div>
    </div>
  );
}
