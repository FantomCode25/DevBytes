import React from 'react'
import DownloadButton from './DownloadButton'

const GUI = () => {
  return (
    <>
    {/* main div */}
      <div className='w-[90vw] justify-evenly flex gap-4 mt-10 mx-auto'>
        {/* left side div */}
        <div>
  <div className='w-[35vw] bg-slate-800 py-5 p-4 rounded-xl shadow-[0_0_60px_rgba(255,255,255,0.5)] hover:shadow-[0_0_80px_rgba(255,255,255,0.6)] transition-shadow duration-500 ease-in-out'>
  <h2 className="text-xl font-semibold text-fuchsia-400">Key Features</h2>
  <ul className="space-y-3 text-sm text-slate-200 my-4.5">
    {[
      'Runs locally for maximum security (tokens stay on the device)',
      'Select repos and moderation targets (issues, PRs, discussions)',
      'Choose actions (delete, hide, close)',
      'Tracks real-time changes to comment status to learn user behavior',
      'Automatically fine-tunes the model based on user behavior',
      'Get detailed insights on spam activity in your repo',
      'Penalize spammers by blocking them directly from the application',
    ].map((text, i) => (
      <li key={i} className="flex items-start gap-3 bg-green-800/20 px-4 py-2 rounded-md shadow-sm">
        <span className="text-green-400 text-lg mt-1">✔</span>
        <span>{text}</span>
      </li>
    ))}
  </ul>
      <br />
      <p className='text-center'>
      Git-Guardian is a secure, adaptive spam moderation tool for GitHub. Built for open-source maintainers, it keeps issues, PRs, and discussions clean with automated moderation, model fine-tuning, and local token security—boosting collaboration while reducing manual effort.
    </p>

    <div className='w-full flex justify-center items-center mt-4'>
      <DownloadButton />
    </div>
  </div>
</div>

        {/* right side div */}
        <div className='flex flex-col gap-5'>
  <img
    className='max-w-[40vw] rounded-xl transition-all duration-500 ease-in-out hover:scale-105 hover:shadow-[0_8px_30px_rgba(232,121,249,0.5)]'
    src='/media/Rahul gui 2.jpeg'
    alt=''
  />
  <img
    className='max-w-[40vw] rounded-xl transition-all duration-500 ease-in-out hover:scale-105 hover:shadow-[0_8px_30px_rgba(232,121,249,0.5)]'
    src='/media/Rahul gui 1.jpeg'
    alt=''
  />
</div>

      </div>
    </>
  )
}

export default GUI
