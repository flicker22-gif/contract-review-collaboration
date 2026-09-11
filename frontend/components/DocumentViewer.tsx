"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import type { Annotation, Paragraph } from "@/lib/api";

export interface SelectionInfo {
  paragraphId: number;
  startOffset: number;
  endOffset: number;
  quotedText: string;
  top: number;
  left: number;
}

interface DocumentViewerProps {
  paragraphs: Paragraph[];
  annotations: Annotation[];
  selectedAnnotationId: number | null;
  canAnnotate: boolean;
  onSelectAnnotation: (id: number) => void;
  onCreateAnnotation: (sel: SelectionInfo, comment: string) => Promise<void>;
  registerHighlightRef: (annotationId: number, el: HTMLElement | null) => void;
}

interface Segment {
  start: number;
  end: number;
  annotation?: Annotation;
}

/** 把段落文本按批注偏移切成若干段，重叠/越界的批注跳过 */
function buildSegments(text: string, annotations: Annotation[]): Segment[] {
  const sorted = [...annotations].sort(
    (a, b) => a.start_offset - b.start_offset
  );
  const segments: Segment[] = [];
  let cursor = 0;
  for (const a of sorted) {
    const s = Math.max(a.start_offset, 0);
    const e = Math.min(a.end_offset, text.length);
    if (s < cursor || e <= s) continue;
    if (s > cursor) segments.push({ start: cursor, end: s });
    segments.push({ start: s, end: e, annotation: a });
    cursor = e;
  }
  if (cursor < text.length) segments.push({ start: cursor, end: text.length });
  return segments;
}

/** 计算 selection 的某个边界点在段落元素内的字符偏移 */
function offsetWithin(container: Node, node: Node, nodeOffset: number): number {
  const range = document.createRange();
  range.selectNodeContents(container);
  range.setEnd(node, nodeOffset);
  return range.toString().length;
}

export default function DocumentViewer({
  paragraphs,
  annotations,
  selectedAnnotationId,
  canAnnotate,
  onSelectAnnotation,
  onCreateAnnotation,
  registerHighlightRef,
}: DocumentViewerProps) {
  const [selection, setSelection] = useState<SelectionInfo | null>(null);
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const annotationsByParagraph = useMemo(() => {
    const map = new Map<number, Annotation[]>();
    for (const a of annotations) {
      const list = map.get(a.paragraph_id) ?? [];
      list.push(a);
      map.set(a.paragraph_id, list);
    }
    return map;
  }, [annotations]);

  const handleMouseUp = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || sel.rangeCount === 0) {
      setSelection(null); // 单击空白处关闭批注弹窗
      return;
    }

    const anchorEl =
      sel.anchorNode instanceof Element
        ? sel.anchorNode
        : sel.anchorNode?.parentElement;
    const focusEl =
      sel.focusNode instanceof Element
        ? sel.focusNode
        : sel.focusNode?.parentElement;
    const paraEl = anchorEl?.closest<HTMLElement>("[data-paragraph-id]");
    const focusParaEl = focusEl?.closest<HTMLElement>("[data-paragraph-id]");

    // 只支持单个段落内划选
    if (!paraEl || paraEl !== focusParaEl) return;

    const paragraphId = Number(paraEl.dataset.paragraphId);
    let start = offsetWithin(paraEl, sel.anchorNode!, sel.anchorOffset);
    let end = offsetWithin(paraEl, sel.focusNode!, sel.focusOffset);
    if (start > end) [start, end] = [end, start];
    if (end - start < 1) return;

    const rect = sel.getRangeAt(0).getBoundingClientRect();
    const containerRect = containerRef.current?.getBoundingClientRect();
    setSelection({
      paragraphId,
      startOffset: start,
      endOffset: end,
      quotedText: paraEl.textContent?.slice(start, end) ?? "",
      top: rect.bottom - (containerRect?.top ?? 0) + 8,
      left: Math.max(
        0,
        Math.min(
          rect.left - (containerRect?.left ?? 0),
          (containerRect?.width ?? 400) - 330
        )
      ),
    });
    setComment("");
  }, []);

  const submitAnnotation = async () => {
    if (!selection || !comment.trim()) return;
    setSubmitting(true);
    try {
      await onCreateAnnotation(selection, comment.trim());
      setSelection(null);
      window.getSelection()?.removeAllRanges();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div ref={containerRef} className="relative" onMouseUp={handleMouseUp}>
      <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
        {paragraphs.map((p) => {
          const segments = buildSegments(
            p.text,
            annotationsByParagraph.get(p.id) ?? []
          );
          return (
            <p
              key={p.id}
              data-paragraph-id={p.id}
              className="mb-3 leading-7 text-gray-800"
            >
              {segments.map((seg, i) => {
                const text = p.text.slice(seg.start, seg.end);
                if (!seg.annotation) return <span key={i}>{text}</span>;
                const a = seg.annotation;
                const isSelected = a.id === selectedAnnotationId;
                return (
                  <mark
                    key={i}
                    ref={(el) => registerHighlightRef(a.id, el)}
                    onClick={() => onSelectAnnotation(a.id)}
                    className={`cursor-pointer rounded-sm px-0.5 transition-shadow ${
                      a.status === "resolved"
                        ? "bg-green-200 hover:bg-green-300"
                        : "bg-yellow-200 hover:bg-yellow-300"
                    } ${isSelected ? "ring-2 ring-amber-500" : ""}`}
                  >
                    {text}
                  </mark>
                );
              })}
            </p>
          );
        })}
      </div>

      {selection && (
        <div
          className="absolute z-20 w-80 rounded-xl border border-gray-200 bg-white p-4 shadow-xl"
          style={{ top: selection.top, left: selection.left }}
          onMouseUp={(e) => e.stopPropagation()}
        >
          <blockquote className="mb-2 max-h-20 overflow-hidden border-l-2 border-amber-400 pl-2 text-xs text-gray-500">
            {selection.quotedText}
          </blockquote>
          {canAnnotate ? (
            <>
              <textarea
                autoFocus
                rows={3}
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="写下风险点或修改建议…"
                className="w-full rounded-lg border border-gray-300 p-2 text-sm outline-none focus:border-blue-500"
              />
              <div className="mt-2 flex justify-end gap-2">
                <button
                  className="rounded-lg px-3 py-1.5 text-sm text-gray-500 hover:bg-gray-100"
                  onClick={() => setSelection(null)}
                >
                  取消
                </button>
                <button
                  disabled={!comment.trim() || submitting}
                  onClick={submitAnnotation}
                  className="rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {submitting ? "提交中…" : "添加批注"}
                </button>
              </div>
            </>
          ) : (
            <p className="text-sm text-amber-600">
              请先在页面右上角填写姓名和角色，再添加批注。
            </p>
          )}
        </div>
      )}
    </div>
  );
}
