"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import UploadZone from "@/components/UploadZone";
import { fetchDocuments, type DocumentListItem } from "@/lib/api";

interface VersionGroup {
  groupId: string;
  latest: DocumentListItem;
  versions: DocumentListItem[]; // 按版本号升序
}

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

  // 同一合同的多个版本归为一组，组按最新版本的上传时间排序
  const groups = useMemo<VersionGroup[]>(() => {
    const map = new Map<string, DocumentListItem[]>();
    for (const doc of documents) {
      const key = doc.group_id ?? `solo-${doc.id}`;
      const list = map.get(key);
      if (list) list.push(doc);
      else map.set(key, [doc]);
    }
    return Array.from(map.entries())
      .map(([groupId, docs]) => {
        const versions = [...docs].sort((a, b) => a.version_number - b.version_number);
        return { groupId, latest: versions[versions.length - 1], versions };
      })
      .sort((a, b) => (a.latest.created_at < b.latest.created_at ? 1 : -1));
  }, [documents]);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">合同审查协作工具</h1>
        <p className="mt-1 text-sm text-gray-500">
          上传合同 → 法务高亮风险条款并批注 → 业务逐条回复 → 新版本上传后可做条款级 diff 对比
        </p>
      </header>

      <UploadZone />

      <section className="mt-10">
        <h2 className="mb-4 text-lg font-semibold text-gray-800">已上传的合同</h2>
        {loading && <p className="text-sm text-gray-400">加载中…</p>}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {!loading && !error && groups.length === 0 && (
          <p className="text-sm text-gray-400">还没有合同，先上传一份吧。</p>
        )}
        <ul className="space-y-3">
          {groups.map((group) => {
            const latest = group.latest;
            return (
              <li
                key={group.groupId}
                className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
              >
                <div className="flex items-center justify-between gap-3">
                  <Link
                    href={`/documents/${latest.id}`}
                    className="flex min-w-0 flex-1 items-center gap-3"
                  >
                    <span className="text-2xl">
                      {latest.file_type === "pdf" ? "📕" : "📘"}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate font-medium text-gray-900">
                        {latest.filename}
                        <span className="ml-2 rounded bg-indigo-100 px-1.5 py-0.5 align-middle text-[11px] font-medium text-indigo-700">
                          最新 v{latest.version_number}
                        </span>
                      </p>
                      <p className="text-xs text-gray-400">
                        {new Date(latest.created_at).toLocaleString("zh-CN")}
                      </p>
                    </div>
                  </Link>
                  <div className="flex shrink-0 items-center gap-2 text-xs">
                    {latest.open_count > 0 && (
                      <span className="rounded-full bg-amber-100 px-2.5 py-1 font-medium text-amber-700">
                        待处理 {latest.open_count}
                      </span>
                    )}
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-gray-600">
                      批注 {latest.annotation_count}
                    </span>
                    {group.versions.length > 1 && (
                      <Link
                        href={`/compare?to=${latest.id}`}
                        className="rounded-full bg-indigo-600 px-2.5 py-1 font-medium text-white hover:bg-indigo-700"
                      >
                        版本对比
                      </Link>
                    )}
                  </div>
                </div>

                {group.versions.length > 1 && (
                  <div className="mt-3 flex flex-wrap items-center gap-1.5 border-t border-gray-100 pt-3">
                    <span className="text-xs text-gray-400">历史版本：</span>
                    {group.versions.map((v) => (
                      <Link
                        key={v.id}
                        href={`/documents/${v.id}`}
                        className={`rounded-full px-2.5 py-0.5 text-xs ${
                          v.id === latest.id
                            ? "bg-indigo-50 font-medium text-indigo-700"
                            : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                        }`}
                        title={`${v.filename} · ${new Date(
                          v.created_at
                        ).toLocaleString("zh-CN")}`}
                      >
                        v{v.version_number}
                        {v.open_count > 0 && (
                          <span className="ml-1 text-amber-600">●{v.open_count}</span>
                        )}
                      </Link>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </section>
    </main>
  );
}
