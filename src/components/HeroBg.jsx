import React from 'react'

const imagesA = [
  '/media/p7.png',
  '/media/p4.png',
  '/media/p5.png',
  '/media/p6.png',
  '/media/o1.png',
  '/media/o2.png',
  '/media/p7.png'
]

const imagesC = [
  '/media/o1.png',
  '/media/o2.png',
  '/media/o3.png',
  '/media/o2.png',
]

const HeroBg = () => {
  return (
    <div className="relative h-screen w-full overflow-hidden text-white">

      {/* Background Grid + Glow */}
      <div className="absolute inset-0 -z-20 bg-slate-900 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:14px_24px] ">
        <div className="absolute left-0 right-0 top-0 -z-10 m-auto h-[310px] w-[310px] rounded-full bg-fuchsia-400 opacity-20 blur-[100px]" />
      </div>

      {/* Main 3 Column Layout */}
      <div className="flex h-[50vh] z-10 relative">

        {/* A: Images moving into Funnel */}
        <div className="relative w-1/4 overflow-hidden mx-auto">
          {imagesA.map((src, idx) => (
            <img
              key={`a-${idx}`}
              src={src}
              alt=""
              className="absolute w-20 h-20 opacity-60 animate-toFunnel"
              style={{
                top: `${Math.random() * 80 + 10}%`,
                left: `-${Math.random() * 100 + 60}px`,
                animationDelay: `${Math.random() * 1}s`
              }}
            />
          ))}
        </div>

        {/* B: Center Funnel */}
          <div className="w-1/3 flex items-center justify-center relative z-10 rounded-full">

          {/* LEFT White Glow */}
          <div className="absolute left-0 top-0 bottom-0 w-10 bg-gradient-to-r from-white/30 to-transparent blur-2xl opacity-40 pointer-events-none" />

          {/* RIGHT White Glow */}
          <div className="absolute right-0 top-0 bottom-0 w-10 bg-gradient-to-l from-white/30 to-transparent blur-2xl opacity-40 pointer-events-none" />

          {/* Funnel Logo + Pulse */}
          <div className="relative flex flex-col justify-center items.center">
            <div className="absolute inset-0 rounded-full bg-fuchsia-500 blur-2xl opacity-20 animate-pulseFunnel" />
            <img className="w-100 max-auto p-3 relative z-10" src="/media/logo.png" alt="logo" />
            <p className="max-w-xl p-2 text-center">
          Keep a watchful eye on your repositories. GitGriffin offers powerful tools for analysis and security, available as a user-friendly Desktop GUI or a seamless GitHub Action.
        </p>
          </div>
          </div>


        {/* C: Images moving away from Funnel */}
        <div className="relative w-1/3 overflow-hidden">
          {imagesC.map((src, idx) => (
            <img
              key={`c-${idx}`}
              src={src}
              alt=""
              className="absolute w-20 h-18 opacity-60 animate-fromFunnel"
              style={{
                top: `${Math.random() * 80 + 10}%`,
                left: `50%`,
                animationDelay: `${Math.random() * 9}s`
              }}
            />
          ))}
        </div>

      </div>
      <iframe className=" flex justify-center items-center w-full h-full" src="./src/comment_stack.html" frameborder="0"></iframe>

    </div>


  )
}

export default HeroBg
