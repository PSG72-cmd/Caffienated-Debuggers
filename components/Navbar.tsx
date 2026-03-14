"use client"

import Link from "next/link"

export default function Navbar() {
  return (
    <div className="flex gap-6 p-4 bg-black text-white border-b">

      <Link href="/dashboard">Dashboard</Link>
      <Link href="/operations">Operations</Link>
      <Link href="/stock">Stock</Link>
      <Link href="/history">Move History</Link>
      <Link href="/settings">Settings</Link>

    </div>
  )
}
