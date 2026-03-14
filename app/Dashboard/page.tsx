"use client"

import Navbar from "@/components/Navbar"

export default function Dashboard() {

 return (
  <div className="bg-black min-h-screen text-white">

   <Navbar/>

   <div className="p-10">

    <h1 className="text-3xl mb-6">
      CoreInventory Dashboard
    </h1>

    <div className="grid grid-cols-2 gap-6">

     <div className="border p-6 rounded">
      <h2 className="text-xl">Receipts</h2>
      <p className="mt-2">4 pending</p>
     </div>

     <div className="border p-6 rounded">
      <h2 className="text-xl">Deliveries</h2>
      <p className="mt-2">4 pending</p>
     </div>

    </div>

   </div>

  </div>
 )
}