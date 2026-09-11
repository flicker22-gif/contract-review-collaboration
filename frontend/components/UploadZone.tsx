"use client";

import { useCallback, useRef, useState } from "react";
import { uploadDocument } from "@/lib/api";
import { useRouter } from "next/navigation";

const ACCEPT = ".docx,.pdf";

export default function UploadZone() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const doUpload = useCallback(
    async (file: File) => {
      setError(null);
      const ext = file.name.toLowerCase().split(".").pop();
      if (ext !== "docx" && ext !== "pdf") {
        setError("仅支持 .docx 或 .pdf 文件");
        return;
      }
      setUploading(true);
      try {
        const doc = await uploadDocument(file);
        router.push(`/documents/${doc.id}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "上传失败");
        setUploading(false);
      }
    },
    [router]
  );

  return (
    <div
      className={`flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-colors ${
        dragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 bg-white hover:border-gray-400"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) doUpload(file);
      }}
    >
      <div className="text-4xl">📄</div>
      <p className="mt-3 text-sm text-gray-600">
        {uploading ? "正在上传并解析…" : "拖拽合同文件到此处，或"}
      </p>
      {!uploading && (
        <button
          className="mt-3 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          onClick={() => inputRef.current?.click()}
        >
          选择文件
        </button>
      )}
      <p className="mt-2 text-xs text-gray-400">支持 Word（.docx）和 PDF</p>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) doUpload(file);
          e.target.value = "";
        }}
      />
    </div>
  );
}
