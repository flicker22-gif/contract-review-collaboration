"use client";

import { useState } from "react";
import type { Annotation } from "@/lib/api";
import { roleBadgeClass, roleLabel, type Identity } from "@/lib/identity";

interface AnnotationCardProps {
  annotation: Annotation;
  paragraphIdx: number | undefined;
  selected: boolean;
  identity: Identity;
  onSelect: () => void;
  onReply: (content: string) => Promise<void>;
  onToggleStatus: () => Promise<void>;
  onDelete: () => Promise<void>;
  cardRef: (el: HTMLElement | null) => void;
}

export default function AnnotationCard({
  annotation,
  paragraphIdx,
  selected,
  identity,
  onSelect,
  onReply,
  onToggleStatus,
  onDelete,
  cardRef,
}: AnnotationCardProps) {
  const [replyDraft, setReplyDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const resolved = annotation.status === "resolved";

  const submitReply = async () => {
    if (!replyDraft.trim()) return;
    setBusy(true);
    try {
      await onReply(replyDraft.trim());
      setReplyDraft("");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      ref={cardRef}
      onClick={onSelect}
      className={`rounded-xl border bg-white p-4 shadow-sm transition-all ${
        selected ? "border-amber-400 ring-2 ring-amber-200" : "border-gray-200"
      } ${resolved ? "opacity-75" : ""}`}
    >
      {/* 引用原文 */}
      <blockquote className="mb-2 border-l-2 border-amber-400 pl-2 text-xs text-gray-500">
        <span className="mr-1 rounded bg-gray-100 px-1 text-gray-400">
          第{paragraphIdx !== undefined ? paragraphIdx + 1 : "?"}段
        </span>
        {annotation.quoted_text}
      </blockquote>

      {/* 批注主体 */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`rounded-full px-2 py-0.5 font-medium ${roleBadgeClass(
              annotation.author_role
            )}`}
          >
            {roleLabel(annotation.author_role)}
          </span>
          <span className="font-medium text-gray-700">
            {annotation.author_name}
          </span>
          <span className="text-gray-400">
            {new Date(annotation.created_at).toLocaleString("zh-CN")}
          </span>
        </div>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
            resolved
              ? "bg-green-100 text-green-700"
              : "bg-amber-100 text-amber-700"
          }`}
        >
          {resolved ? "已解决" : "待处理"}
        </span>
      </div>
      <p className="mt-2 whitespace-pre-wrap text-sm text-gray-800">
        {annotation.comment}
      </p>

      {/* 回复线程 */}
      {annotation.replies.length > 0 && (
        <div className="mt-3 space-y-2 border-t border-gray-100 pt-3">
          {annotation.replies.map((reply) => (
            <div key={reply.id} className="rounded-lg bg-gray-50 p-2.5">
              <div className="flex items-center gap-2 text-xs">
                <span
                  className={`rounded-full px-2 py-0.5 font-medium ${roleBadgeClass(
                    reply.author_role
                  )}`}
                >
                  {roleLabel(reply.author_role)}
                </span>
                <span className="font-medium text-gray-700">
                  {reply.author_name}
                </span>
                <span className="text-gray-400">
                  {new Date(reply.created_at).toLocaleString("zh-CN")}
                </span>
              </div>
              <p className="mt-1 whitespace-pre-wrap text-sm text-gray-700">
                {reply.content}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* 回复输入 */}
      <div className="mt-3 flex gap-2">
        <input
          value={replyDraft}
          onChange={(e) => setReplyDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.nativeEvent.isComposing) submitReply();
          }}
          onClick={(e) => e.stopPropagation()}
          placeholder={
            identity.name ? "回复…" : "请先在页面右上角填写姓名"
          }
          disabled={!identity.name}
          className="min-w-0 flex-1 rounded-lg border border-gray-300 px-2.5 py-1.5 text-sm outline-none focus:border-blue-500 disabled:bg-gray-50"
        />
        <button
          onClick={(e) => {
            e.stopPropagation();
            submitReply();
          }}
          disabled={!replyDraft.trim() || busy || !identity.name}
          className="shrink-0 rounded-lg bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          回复
        </button>
      </div>

      {/* 操作 */}
      <div className="mt-3 flex justify-end gap-3 border-t border-gray-100 pt-2 text-xs">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleStatus();
          }}
          className={
            resolved
              ? "text-amber-600 hover:underline"
              : "text-green-600 hover:underline"
          }
        >
          {resolved ? "重新打开" : "标记已解决"}
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm("确定删除这条批注及其所有回复吗？")) onDelete();
          }}
          className="text-red-500 hover:underline"
        >
          删除
        </button>
      </div>
    </div>
  );
}
