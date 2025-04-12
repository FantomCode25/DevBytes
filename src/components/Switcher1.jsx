import React, { useState } from 'react'

const Switcher1 = () => {
  const [isChecked, setIsChecked] = useState(false)

  const handleCheckboxChange = () => {
    setIsChecked(!isChecked)
  }

  return (
    
    <div className="flex justify-center items-center">
      <label className='flex cursor-pointer select-none items-center'>
        <div className='relative'>
          <input
            type='checkbox'
            checked={isChecked}
            onChange={handleCheckboxChange}
            className='sr-only'
          />
          {/* Background */}
          <div className={`block h-8 w-14 rounded-full transition-colors duration-300 ${
            isChecked ? 'bg-fuchsia-500' : 'bg-gray-300'
          }`} />
          {/* Toggle Circle */}
          <div
            className={`dot absolute top-1 h-6 w-6 rounded-full bg-white transition-transform duration-300 ${
              isChecked ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </div>
      </label>
    </div>
  )
}

export default Switcher1
