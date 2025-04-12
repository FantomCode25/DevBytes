import { useState } from 'react'
import './App.css'
import GUI from './components/GUI'
import Github_Action from './components/Github_Action'
import HeroBg from './components/HeroBg'
import Switcher1 from './components/Switcher1';



function App() {
  return (
    <>
    {/* Hero section with animated background */}
      <HeroBg/>
      <div style={{ padding: 20 }} className=' bg-slate-900 text-white'>
      <div className='flex items-center gap-4 justify-center align-middle '>
        <div className='font-bold'>Desktop Application</div>
        <button
      className='bg-fuchsia-500 px-4 py-2 text-lg rounded-xl shadow-md shadow-fuchsia-300 hover:shadow-fuchsia-500 hover:shadow-2xl transition-shadow duration-500 ease-in-out hover:cursor-pointer my-2 flex gap-1 font-bold'
    >
      Github Action
      <img className='invert w-6 ml-1' src="/media/github.svg" alt="" />
    </button>
      </div>
      
      <GUI/>
    </div>
    </>
  )
}

export default App
