"use client"

import Navbar from "@/components/Navbar"

export default function Stock(){

 return(
  <div className="bg-black min-h-screen text-white">

   <Navbar/>

   <div className="p-10">

    <h1 className="text-2xl mb-6">Stock</h1>

    <table className="w-full border">

     <thead>
      <tr>
       <th>Product</th>
       <th>Cost</th>
       <th>On Hand</th>
       <th>Free to Use</th>
      </tr>
     </thead>

     <tbody>
      <tr>
       <td>Desk</td>
       <td>3000 Rs</td>
       <td>50</td>
       <td>45</td>
      </tr>

      <tr>
       <td>Table</td>
       <td>3000 Rs</td>
       <td>50</td>
       <td>50</td>
      </tr>
     </tbody>

    </table>

   </div>

  </div>
 )
}