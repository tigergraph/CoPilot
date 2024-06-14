import 'react-chatbot-kit/build/main.css';
import { useEffect, useState } from 'react';
import Chatbot from 'react-chatbot-kit';
import ActionProvider from '../actions/ActionProvider.js';
import config from "../actions/config.js";
import MessageParser from "../actions/MessageParser.js";
import { MdKeyboardArrowDown } from "react-icons/md";

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"


const Bot = ({ layout }: { layout?: string | undefined }) => {
  const [store, setStore] = useState<any>();

  useEffect(() => {
    const parseStore = JSON.parse(localStorage.getItem('site') || '{}');
    setStore(parseStore)
  }, []);

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

          {/* <div className='text-sm flex items-center border p-2 border-gray-300 dark:border-[#3D3D3D] rounded-md mr-16'>
            <img src="/graph-icon.svg" alt="" className="mr-2"/>
            Transaction Fraud
            <MdKeyboardArrowDown className='text-2xl'/>
          </div> */}

          <DropdownMenu>

            <DropdownMenuTrigger asChild className='mr-20'>
              <Button variant='outline' className='!h-[48px] !outline-b !outline-gray-300 dark:!outline-[#3D3D3D] h-[70px] flex justify-end items-center bg-white dark:bg-background z-50 rounded-tr-lg'><img src="/graph-icon.svg" alt="" className="mr-2"/>Transaction Fraud <MdKeyboardArrowDown className='text-2xl'/></Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent className="w-56">
              <DropdownMenuLabel>Select a Graph</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>

                {store?.graphs.map((f,i) => (

                  <DropdownMenuItem key={i}>
                    {/* <User className="mr-2 h-4 w-4" /> */}
                    <span>Profile</span>
                    <a href='#'>{f}</a>
                    {/* <DropdownMenuShortcut>⇧⌘P</DropdownMenuShortcut> */}
                  </DropdownMenuItem>

                ))}

              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>





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
