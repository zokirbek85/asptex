"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
  type ColumnDef,
  type SortingState,
  getSortedRowModel,
  type PaginationState,
} from "@tanstack/react-table";
import { ChevronDown, ChevronUp, ChevronsLeft, ChevronLeft, ChevronRight, ChevronsRight } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { Button } from "./Button";

interface DataTableProps<TData> {
  data: TData[];
  columns: ColumnDef<TData, unknown>[];
  // Server-side pagination (pass these when the parent owns pagination state)
  pageCount?: number;
  pagination?: PaginationState;
  onPaginationChange?: (updater: PaginationState | ((prev: PaginationState) => PaginationState)) => void;
  isLoading?: boolean;
  emptyText?: string;
  className?: string;
}

export function DataTable<TData>({
  data,
  columns,
  pageCount,
  pagination,
  onPaginationChange,
  isLoading = false,
  emptyText = "No data",
  className,
}: DataTableProps<TData>) {
  const [sorting, setSorting] = useState<SortingState>([]);

  const serverPaginated = pageCount !== undefined && pagination !== undefined;

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onSortingChange: setSorting,
    ...(serverPaginated
      ? {
          pageCount,
          state: { sorting, pagination },
          onPaginationChange: onPaginationChange as (
            updater: PaginationState | ((prev: PaginationState) => PaginationState)
          ) => void,
          manualPagination: true,
        }
      : { state: { sorting } }),
  });

  return (
    <div className={cn("flex flex-col gap-3", className)}>
      <div className="overflow-x-auto rounded-lg border border-gray-200">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id}>
                {hg.headers.map((header) => (
                  <th
                    key={header.id}
                    className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wide whitespace-nowrap"
                    style={{ width: header.getSize() !== 150 ? header.getSize() : undefined }}
                  >
                    {header.isPlaceholder ? null : (
                      <div
                        className={cn(
                          "flex items-center gap-1",
                          header.column.getCanSort() && "cursor-pointer select-none hover:text-gray-900"
                        )}
                        onClick={header.column.getToggleSortingHandler()}
                      >
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {header.column.getIsSorted() === "asc" && <ChevronUp size={12} />}
                        {header.column.getIsSorted() === "desc" && <ChevronDown size={12} />}
                      </div>
                    )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-gray-100 bg-white">
            {isLoading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-400">
                  <div className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Loading…
                  </div>
                </td>
              </tr>
            ) : table.getRowModel().rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-8 text-center text-gray-400">
                  {emptyText}
                </td>
              </tr>
            ) : (
              table.getRowModel().rows.map((row) => (
                <tr key={row.id} className="hover:bg-gray-50 transition-colors">
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 text-gray-700">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {serverPaginated && pageCount! > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Page {table.getState().pagination.pageIndex + 1} of {pageCount}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => table.setPageIndex(0)}
              disabled={!table.getCanPreviousPage()}
            >
              <ChevronsLeft size={15} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
            >
              <ChevronLeft size={15} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
            >
              <ChevronRight size={15} />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => table.setPageIndex(pageCount! - 1)}
              disabled={!table.getCanNextPage()}
            >
              <ChevronsRight size={15} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
