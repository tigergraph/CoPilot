import "react-chatbot-kit/build/main.css";
import { useEffect, useState } from "react";
import Chatbot from "react-chatbot-kit";
import ActionProvider from "../actions/ActionProvider.js";
import config from "../actions/config.js";
import MessageParser from "../actions/MessageParser.js";
import { MdKeyboardArrowDown } from "react-icons/md";
import { SelectedGraphContext } from './Contexts.js';

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const Bot = ({ layout, getConversationId }: { layout?: string | undefined, getConversationId?:any }) => {
  const [store, setStore] = useState<any>();
  const [currentDate, setCurrentDate] = useState('');
  const [selectedGraph, setSelectedGraph] = useState(localStorage.getItem("selectedGraph") || 'pyTigerGraphRAG');
  const [ragPattern, setRagPattern] = useState(localStorage.getItem("ragPattern") || 'HNSW_Overlap');

  useEffect(() => {
    const parseStore = JSON.parse(localStorage.getItem("site") || "{}");
    setStore(parseStore);

    const date = new Date();
    const options: Intl.DateTimeFormatOptions = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' };
    const formattedDate = date.toLocaleDateString('en-US', options);
    setCurrentDate(formattedDate);
  }, []);

  const handleSelect = (value) => {
    setSelectedGraph(value);
    localStorage.setItem("selectedGraph", value);
    window.location.reload();
  };

  const handleSelectRag = (value) => {
    setRagPattern(value);
    localStorage.setItem("ragPattern", value);
    window.location.reload();
  };

  return (
    <div className={layout}>
      {/* {layout === "fp" && ( */}
        <div className="border-b border-gray-300 dark:border-[#3D3D3D] h-[70px] flex justify-end items-center bg-white dark:bg-background z-50 rounded-tr-lg">
          <div className="text-sm pl-5 mr-auto">{currentDate}</div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild className="mr-20">
              <Button
                variant="outline"
                className="!h-[48px] !outline-b !outline-gray-300 dark:!outline-[#3D3D3D] h-[70px] flex justify-end items-center bg-white dark:bg-background z-50 rounded-tr-lg"
              >
                <img src="/graph-icon.svg" alt="" className="mr-2" />
                {ragPattern} <MdKeyboardArrowDown className="text-2xl" />
              </Button>
            </DropdownMenuTrigger>

            <DropdownMenuContent className="w-56">
              <DropdownMenuLabel>Select a RAG Pattern</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuGroup>
                {["HNSW", "HNSW_Overlap", "Sibling"].map((f, i) => (
                  <DropdownMenuItem key={i} onSelect={() => handleSelectRag(f)}>
                    {/* <User className="mr-2 h-4 w-4" /> */}
                    <span>{f}</span>
                    {/* <DropdownMenuShortcut>⇧⌘P</DropdownMenuShortcut> */}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
          <DropdownMenu>
            <DropdownMenuTrigger asChild className="mr-20">
              <Button
                variant="outline"
                className="!h-[48px] !outline-b !outline-gray-300 dark:!outline-[#3D3D3D] h-[70px] flex justify-end items-center bg-white dark:bg-background z-50 rounded-tr-lg"
              >
                <img src="/graph-icon.svg" alt="" className="mr-2" />
                {selectedGraph} <MdKeyboardArrowDown className="text-2xl" />
              </Button>
            </DropdownMenuTrigger>

          <DropdownMenuContent className="w-56">
            <DropdownMenuLabel>Select a Graph</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              {store?.graphs.map((f, i) => (
                <DropdownMenuItem key={i} onSelect={() => handleSelect(f)}>
                  <span>{f}</span>
                </DropdownMenuItem>
              ))}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      
      <SelectedGraphContext.Provider value={selectedGraph}>
        <Chatbot
          // eslint-disable-next-line
          // @ts-ignore
          config={config}
          fullPage={layout}
          getConversationId={getConversationId}
          messageParser={MessageParser}
          actionProvider={ActionProvider}
        />
      </SelectedGraphContext.Provider>
    </div>
  );
};

export default Bot;
