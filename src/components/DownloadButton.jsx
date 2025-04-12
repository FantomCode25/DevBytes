import React from 'react'

const handleDownload = () => {
  const file = '/GitGriffin.exe.zip'
  const link = document.createElement('a')
  link.href = file
  link.download = 'GitGriffin.exe.zip'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

const DownloadButton = () => {
  return (
    <button
      onClick={handleDownload}
      className='bg-fuchsia-500 px-4 py-2 text-lg rounded-xl shadow-md shadow-fuchsia-300 hover:shadow-fuchsia-500 hover:shadow-2xl transition-shadow duration-500 ease-in-out hover:cursor-pointer my-2 flex gap-1'
    >
      Download Now
      <img className='invert w-5' src="/media/download.svg" alt="" />
    </button>
  )
}

export default DownloadButton
