import { FC } from "react";
import { FaRegThumbsUp } from "react-icons/fa";
import { FaRegThumbsDown } from "react-icons/fa";
import { PiGraph } from "react-icons/pi";
import { IoMdCopy } from "react-icons/io";
import { PiArrowsCounterClockwiseFill } from "react-icons/pi";
import { LuInfo } from "react-icons/lu";

import { SetStateAction } from "react";

// interface IChatbotMessageProps {
//   message?: any;
// }
interface IChatbotMessageProps {
  message?: any;
  withAvatar?: boolean;
  loading?: boolean;
  messages: any[];
  delay?: number;
  id: number;
  setState?: React.Dispatch<any>;
  customComponents?: any;
  customStyles: {
  backgroundColor: string;
  };
}

export const CustomChatMessage: FC<IChatbotMessageProps> = ({ message }: IChatbotMessageProps) => {

  // const convertString = (str: any) => {
  //   if(str.indexOf('{') > -1) {
  //     const jsonStr = str.replace(/(\w+:)|(\w+ :)/g, function(matchedStr) {
  //       return '"' + matchedStr.substring(0, matchedStr.length - 1) + '":';
  //     });
  //     str = JSON.parse(jsonStr);
  //     return str.action_input;
  //   } else {
  //     return str;
  //   }
  // }

  return (
    <>
      {message ? (
        <div className="text-sm max-w-[230px] md:max-w-[80%] mt-7 mb-7">
          <p className="type-writer">{message.natural_language_response}</p>
          <div className="flex mt-3">

            <div className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer" onClick={() => alert('Like!!')}>
              <FaRegThumbsUp />
            </div>
            <div className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer" onClick={() => alert('DisLike!!')}>
              <FaRegThumbsDown />
            </div>
            <div className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer" onClick={() => alert('Copy!!')}>
              <IoMdCopy className='text-[15px]' />
            </div>
            <div className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer" onClick={() => alert('Regenerate!!')}>
              <PiArrowsCounterClockwiseFill className='text-[15px]' />
            </div>
            <div className="w-auto h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 px-2 cursor-pointer" onClick={() => alert('explain!!')}>
              <LuInfo className='text-[15px] mr-1' />
              <span className="text-xs">Explain</span>
            </div>
          
          </div>
        </div>
      ) : <div>The chatbot is currently down for maintenance.</div>}
      {/* OLD */}
      {/* {message ? (
        <div className="text-sm max-w-[230px] md:max-w-[80%] mt-7 mb-7">{message.natural_language_response ? (
          <>
            <p>{convertString(message.natural_language_response)}</p>

            <div className="flex mt-3">
              <FaRegThumbsUp className="mr-1" onClick={() => alert('Like!!')} />
              <FaRegThumbsDown onClick={() => alert('DisLike!!')} />
              <PiGraph className='text-[15px] mr-1' onClick={() => alert('graph!!')} />
              <IoMdCopy className='text-[15px]' onClick={() => alert('copy!!')} />
            </div>

            {message.query_sources.reasoning ? (
              <p className="text-[11px] rounded-md bg-[#ececec] dark:bg-shadeA mt-3 p-4 leading-4">
                <strong>Reasoning:</strong> {message.query_sources.reasoning}
              </p>
            ) : null}

            {message.query_sources.result ? (
              <p className="text-[11px] rounded-md bg-[#ececec] dark:bg-shadeA mt-3 p-4 leading-4">
                <strong>Result:</strong> {message.query_sources.result}
              </p>
            ) : null}

          </>
        ) : message}</div>
      ) : null} */}
    </>
  );
};


