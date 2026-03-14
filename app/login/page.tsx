export default function Login(){

 return(
  <div className="flex items-center justify-center h-screen bg-black text-white">

   <div className="border p-10 rounded w-96">

    <h1 className="text-xl mb-4">Login</h1>

    <input
     className="w-full p-2 mb-3 bg-black border"
     placeholder="Login ID"
    />

    <input
     type="password"
     className="w-full p-2 mb-3 bg-black border"
     placeholder="Password"
    />

    <button className="w-full bg-white text-black p-2">
     Sign In
    </button>

   </div>

  </div>
 )
}