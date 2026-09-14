"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import DiffView from "@/components/DiffView";
import {
  fetchDiff,
  fetchVersions,
  type DiffResponse,
  type VersionInfo,
} from "@/lib/api";

function formatTime(iso: string) {
  return new Date(iso).toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function CompareInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const newIdFromUrl = Number(searchParams.get("to") ?? searchParams.get("new") ?? "");
  const oldIdFromUrl = Number(searchParams.get("from") ?? searchParams.get("old") ?? "");

  const [versions, setVersions] = useState<VersionInfo[]>([]);
  const [diff, setDiff] = useState<DiffResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [onlyChanges, setOnlyChanges] = useState(true);

  useEffect(() => {
    if (!Number.isFinite(newIdFromUrl) || newIdFromUrl === 0) {
      setError("缺少要对比的合同版本");
      setVersions([]);
      setDiff(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    // 先取版本链，确定旧版（URL 指定优先，否则默认上一版），再取 diff
    fetchVersions(newIdFromUrl)
      .then(async (vs) => {
        if (cancelled) return;
        setVersions(vs);
        if (!cancelled) setVersions(vs);
        let oldParam: number | undefined;
        if (Number.isFinite(oldIdFromUrl) && oldIdFromUrl !== 0) {
          oldParam = oldIdFromUrl;
        } else {
          const current = vs.find((v) => v.id === newIdFromUrl);
          if (current && current.version_number > 1) {
            const prev = vs.find(
              (v) => v.version_number === current.version_number - 1
            );
            if (prev) oldParam = prev.id;
          }
        }
        if (oldParam === undefined || oldParam === newIdFromUrl) {
          // 只有一个版本，无法对比
          if (!cancelled) setDiff(null);
          return;
        }
        const d = await fetchDiff(newIdFromUrl, oldParam);
        if (!cancelled) setDiff(d);
      })
      .catch((e) => {
        if (cancelled) return;
        setDiff(null);
        setError(e instanceof Error ? e.message : "对比失败");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [newIdFromUrl, oldIdFromUrl]);

  const onSelect = useCallback(
    (which: "old" | "new", id: number) => {
      const params = new URLSearchParams();
      if (which === "new") {
        params.set("to", String(id));
        // 旧版缺省由新版的版本链自动决定（上一版）
      } else {
        params.set("to", String(newIdFromUrl));
        params.set("from", String(id));
      }
      router.push(`/compare?${params.toString()}`);
    },
    [newIdFromUrl, router]
  );

  const stats = diff?.stats;
  const shownRows = useMemo(() => diff?.rows ?? [], [diff]);

  if (error && !loading) {
    return (
      <main className="mx-auto max-w-4xl px-6 py-10">
        <p className="text-red-600">{error}</p>
        <Link href="/" className="mt-2 inline-block text-sm text-blue-600 hover:underline">
          ← 返回列表
        </Link>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-4xl px-6 py-8">
      <header className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/" className="text-sm text-blue-600 hover:underline">
            ← 返回列表
          </Link>
          <h1 className="mt-1 text-xl font-bold text-gray-900">版本对比</h1>
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={onlyChanges}
            onChange={(e) => setOnlyChanges(e.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-blue-600"
          />
          仅看变动条款
        </label>
      </header>

      {/* 版本选择器 */}
      <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl border border-gray-200 bg-white p-3 shadow-sm">
        <VersionSelect
          label="旧版"
          versions={versions}
          value={diff?.old.id}
          excludeId={diff?.new.id}
          onChange={(id) => onSelect("old", id)}
        />
        <span className="px-1 text-lg text-gray-400">→</span>
        <VersionSelect
          label="新版"
          versions={versions}
          value={newIdFromUrl}
          excludeId={diff?.old.id}
          onChange={(id) => onSelect("new", id)}
        />
        <div className="ml-auto flex items-center gap-3 text-xs text-gray-400">
          {diff && (
            <>
              <span>旧版 {formatTime(diff.old.created_at)}</span>
              <span>·</span>
              <span>新版 {formatTime(diff.new.created_at)}</span>
            </>
          )}
        </div>
      </div>

      {/* 变动统计 */}
      {stats && (
        <div className="mb-4 flex flex-wrap gap-2 text-sm">
          <span className="rounded-full bg-green-100 px-3 py-1 font-medium text-green-700">
            新增 {stats.added} 段
          </span>
          <span className="rounded-full bg-red-100 px-3 py-1 font-medium text-red-700">
            删除 {stats.deleted} 段
          </span>
          <span className="rounded-full bg-amber-100 px-3 py-1 font-medium text-amber-700">
            修改 {stats.modified} 段
          </span>
          <span className="rounded-full bg-gray-100 px-3 py-1 text-gray-500">
            未变 {stats.unchanged} 段
          </span>
          <span className="ml-auto self-center text-xs text-gray-400">
            字符 +{stats.added_chars} / −{stats.deleted_chars}
          </span>
        </div>
      )}

      {loading ? (
        <p className="py-16 text-center text-sm text-gray-400">正在对比两版内容…</p>
      ) : diff ? (
        diff.rows.filter((r) => r.type !== "equal").length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-10 text-center shadow-sm">
            <p className="text-2xl">✅</p>
            <p className="mt-2 text-sm text-gray-500">两个版本内容完全一致，没有变动。</p>
          </div>
        ) : (
          <DiffView rows={shownRows} onlyChanges={onlyChanges} />
        )
      ) : (
        !error && (
          <div className="rounded-xl border border-gray-200 bg-white p-10 text-center shadow-sm">
            <p className="text-2xl">📑</p>
            <p className="mt-2 text-sm text-gray-500">
              这份合同目前只有一个版本。可在审查页点击「上传新版本」后再做对比。
            </p>
            <Link
              href={`/documents/${newIdFromUrl}`}
              className="mt-3 inline-block text-sm text-blue-600 hover:underline"
            >
              前往上传新版本 →
            </Link>
          </div>
        )
      )}

      {/* 快捷入口 */}
      {diff && (
        <div className="mt-4 flex justify-end gap-4 text-sm">
          <Link
            href={`/documents/${diff.old.id}`}
            className="text-blue-600 hover:underline"
          >
            打开旧版审查页（v{diff.old.version_number}）
          </Link>
          <Link
            href={`/documents/${diff.new.id}`}
            className="text-blue-600 hover:underline"
          >
            打开新版审查页（v{diff.new.version_number}）
          </Link>
        </div>
      )}
    </main>
  );
}

function VersionSelect({
  label,
  versions,
  value,
  excludeId,
  onChange,
}: {
  label: string;
  versions: VersionInfo[];
  value?: number | null;
  excludeId?: number;
  onChange: (id: number) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-500">{label}</span>
      <select
        value={value ?? ""}
        disabled={versions.length === 0}
        onChange={(e) => onChange(Number(e.target.value))}
        className="rounded-lg border border-gray-300 px-2 py-1.5 text-sm outline-none focus:border-blue-500"
      >
        {versions.map((v) => (
          <option key={v.id} value={v.id} disabled={v.id === excludeId}>
            v{v.version_number} · {v.filename}
            {v.open_count > 0 ? `（待处理 ${v.open_count}）` : ""}
          </option>
        ))}
      </select>
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto max-w-4xl px-6 py-10 text-gray-400">加载中…</main>
      }
    >
      <CompareInner />
    </Suspense>
  );
}
