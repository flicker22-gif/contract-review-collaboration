"use client";

import type { DiffRow, DiffToken } from "@/lib/api";

/** 渲染内联 token：删除红色删除线，新增绿色 */
function InlineTokens({ tokens }: { tokens: DiffToken[] }) {
  return (
    <>
      {tokens.map((tok, i) => {
        if (tok.op === "equal") return <span key={i}>{tok.v}</span>;
        const isInsert = tok.op === "insert";
        const cls = isInsert
          ? "bg-green-200/70 text-green-900 rounded-sm px-0.5"
          : "bg-red-200/70 text-red-900 rounded-sm px-0.5 line-through decoration-red-500/60";
        return (
          <span key={i} className={cls}>
            {tok.v}
          </span>
        );
      })}
    </>
  );
}

function GutterLabel({ idx }: { idx: number | null }) {
  return (
    <span className="w-9 shrink-0 select-none text-right font-mono text-[11px] leading-7 text-gray-400">
      {idx === null ? "" : `§${idx + 1}`}
    </span>
  );
}

function ChangeMarker({ mark, tone }: { mark: string; tone: "green" | "red" | "gray" }) {
  const colors = {
    green: "bg-green-100 text-green-700",
    red: "bg-red-100 text-red-600",
    gray: "bg-gray-100 text-gray-400",
  }[tone];
  return (
    <span
      className={`flex h-6 w-6 shrink-0 items-center justify-center rounded text-sm font-bold ${colors}`}
    >
      {mark}
    </span>
  );
}

export default function DiffView({
  rows,
  onlyChanges,
}: {
  rows: DiffRow[];
  onlyChanges: boolean;
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm sm:p-8">
      <div className="space-y-1">
        {rows.map((row, i) => {
          if (row.type === "equal") {
            if (onlyChanges) return null;
            return (
              <div key={i} className="flex items-start gap-2 px-1 text-gray-500">
                <GutterLabel idx={row.new_idx} />
                <ChangeMarker mark="" tone="gray" />
                <p className="flex-1 whitespace-pre-wrap leading-7">{row.text}</p>
              </div>
            );
          }

          if (row.type === "added") {
            return (
              <div
                key={i}
                className="flex items-start gap-2 rounded-lg bg-green-50 px-2 py-1 ring-1 ring-green-100"
              >
                <GutterLabel idx={row.new_idx} />
                <ChangeMarker mark="+" tone="green" />
                <p className="flex-1 whitespace-pre-wrap leading-7 text-green-900">
                  <InlineTokens
                    tokens={[{ op: "insert", v: row.text ?? "" }]}
                  />
                </p>
              </div>
            );
          }

          if (row.type === "deleted") {
            return (
              <div
                key={i}
                className="flex items-start gap-2 rounded-lg bg-red-50 px-2 py-1 ring-1 ring-red-100"
              >
                <GutterLabel idx={row.old_idx} />
                <ChangeMarker mark="−" tone="red" />
                <p className="flex-1 whitespace-pre-wrap leading-7 text-red-900">
                  <InlineTokens
                    tokens={[{ op: "delete", v: row.text ?? "" }]}
                  />
                </p>
              </div>
            );
          }

          // modified：旧版一行（删除部分高亮）+ 新版一行（新增部分高亮）
          return (
            <div
              key={i}
              className="space-y-0.5 rounded-lg bg-amber-50/50 px-2 py-1.5 ring-1 ring-amber-100"
            >
              <div className="flex items-start gap-2">
                <GutterLabel idx={row.old_idx} />
                <ChangeMarker mark="−" tone="red" />
                <p className="flex-1 whitespace-pre-wrap leading-7 text-gray-700">
                  <InlineTokens tokens={row.old_tokens} />
                </p>
              </div>
              <div className="flex items-start gap-2">
                <GutterLabel idx={row.new_idx} />
                <ChangeMarker mark="+" tone="green" />
                <p className="flex-1 whitespace-pre-wrap leading-7 text-gray-800">
                  <InlineTokens tokens={row.new_tokens} />
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
