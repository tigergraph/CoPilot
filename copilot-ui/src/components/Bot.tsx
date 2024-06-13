import 'react-chatbot-kit/build/main.css';
import Chatbot from 'react-chatbot-kit';
import ActionProvider from '../actions/ActionProvider.js';
import config from "../actions/config.js";
import MessageParser from "../actions/MessageParser.js";
import { MdKeyboardArrowDown } from "react-icons/md";

const Bot = ({ layout }: { layout?: string | undefined }) => {
  return (
    <div className={layout}>

      {layout === 'fp' && (
        <div className='border-b border-gray-300 dark:border-[#3D3D3D] h-[70px] flex justify-end items-center bg-white dark:bg-background z-50 rounded-tr-lg'>
          <div className='text-sm pl-5 mr-auto'>May 21, Tuesday</div>
          <div className='text-sm flex items-center border dark:border-[#3D3D3D] p-2 border-gray-300 rounded-md mr-5'>
            <img src="/workgroup-icon.svg" alt="" className="mr-2"/>
            Workgroup-2024-04-24-uxWr...
            <MdKeyboardArrowDown className='text-2xl' />
          </div>
          <div className='text-sm flex items-center border p-2 border-gray-300 dark:border-[#3D3D3D] rounded-md mr-16'>
            <img src="/graph-icon.svg" alt="" className="mr-2"/>
            Transaction Fraud
            <MdKeyboardArrowDown className='text-2xl'/>
          </div>
        </div>
      )}
      
      <Chatbot
        // eslint-disable-next-line
        // @ts-ignore
        config={config}
        fullPage={layout}
        messageParser={MessageParser}
        actionProvider={ActionProvider}
      />
    </div>
  );
};

export default Bot;
