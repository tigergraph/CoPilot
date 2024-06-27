import { FC, useState } from "react";
import {
  FaRegThumbsUp,
  FaThumbsUp,
  FaRegThumbsDown,
  FaThumbsDown,
} from "react-icons/fa";
import { PiGraph } from "react-icons/pi";
import { IoMdCopy } from "react-icons/io";
import { PiArrowsCounterClockwiseFill } from "react-icons/pi";
import { LuInfo } from "react-icons/lu";
import { Feedback, Message } from "@/actions/ActionProvider";
import Markdown from 'react-markdown'

const COPILOT_URL = "";
// const COPILOT_URL = "http://0.0.0.0:8000";
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

const urlRegex = /https?:\/\//
const getReasoning = (msg) => {
  // handle list
  
  if(msg.query_sources.reasoning instanceof Array) {
    let sources:Array<JSX.Element> = []
    for(let i = 0; i < msg.query_sources.reasoning.length; i++){
      const src = msg.query_sources.reasoning[i]
      if(urlRegex.test(src)){
        const a = (<li key={src}><a href={src} target='_blank' className='underline overflow-auto'>{src}</a></li>)
        sources.push(a)
      } else{
        const a = (<li key={src}>{src}</li>)
        sources.push(a)
      }
    }
    return (
      <ul className='overflow-hidden'>
        {sources}
      </ul>
    )
  }
  return msg.query_sources.reasoning
}

export const CustomChatMessage: FC<IChatbotMessageProps> = ({
  message,
}: IChatbotMessageProps) => {
  const [showResult, setShowResult] = useState(false);
  const [feedback, setFeedback] = useState(Feedback.NoFeedback);

  const explain = () => {
    setShowResult((prev) => !prev);
  };

  const sendFeedback = async (action: Feedback, message: Message) => {
    const creds = localStorage.getItem("creds");
    setFeedback(action);
    message.feedback = action;
    await fetch(`${COPILOT_URL}/ui/feedback`, {
      method: "POST",
      body: JSON.stringify(message),
      headers: {
        Authorization: `Basic ${creds}`,
        "Content-Type": "application/json",
      },
    });
  };
  // TODO
  // const determineContentType = (message: any) => {}

  return (
    <>
      {typeof message === "string" ? (
        <div className="text-sm max-w-[230px] md:max-w-[80%] mt-7 mb-7">
          <p className="typewriter">{message}</p>
          <div className="flex mt-3">
            <div
              className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer"
              onClick={() => alert("Like!!")}
            >
              <FaRegThumbsUp />
            </div>
            <div
              className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer"
              onClick={() => alert("DisLike!!")}
            >
              <FaRegThumbsDown />
            </div>
            <div
              className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer"
              onClick={() => alert("Copy!!")}
            >
              <IoMdCopy className="text-[15px]" />
            </div>
            <div
              className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer"
              onClick={() => alert("Regenerate!!")}
            >
              <PiArrowsCounterClockwiseFill className="text-[15px]" />
            </div>
            <div
              className="w-auto h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 px-2 cursor-pointer"
              onClick={() => explain()}
            >
              <LuInfo className="text-[15px] mr-1" />
              <span className="text-xs">Explain</span>
            </div>
          </div>
        </div>
      ) : message.key === null ? (
        message
      ) : (
        <div className="text-sm max-w-[230px] md:max-w-[80%] mt-7 mb-7">
          {message.response_type === "progress" ? (
            <p className="copilot-thinking typewriter">{message.content}</p>
          ) : (
            <Markdown className="typewriter">{message.content}</Markdown>
          )}
          <div className="flex mt-3">
            <div
              className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer"
              onClick={() => {
                if (feedback !== Feedback.LIKE) {
                  sendFeedback(Feedback.LIKE, message);
                } else {
                  sendFeedback(Feedback.NoFeedback, message);
                }
              }}
            >
              {feedback === Feedback.LIKE ? <FaThumbsUp /> : <FaRegThumbsUp />}
            </div>
            <div
              className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer"
              onClick={() => {
                if (feedback !== Feedback.DISLIKE) {
                  sendFeedback(Feedback.DISLIKE, message);
                } else {
                  sendFeedback(Feedback.NoFeedback, message);
                }
              }}
            >
              {feedback === Feedback.DISLIKE ? (
                <FaThumbsDown />
              ) : (
                <FaRegThumbsDown />
              )}
            </div>
            <div
              className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer"
              onClick={() => alert("Copy!!")}
            >
              <IoMdCopy className="text-[15px]" />
            </div>
            <div
              className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer"
              onClick={() => alert("Regenerate!!")}
            >
              <PiArrowsCounterClockwiseFill className="text-[15px]" />
            </div>
            <div
              className="w-auto h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 px-2 cursor-pointer"
              onClick={() => explain()}
            >
              <LuInfo className="text-[15px] mr-1" />
              <span className="text-xs">Explain</span>
            </div>
          </div>

          {showResult ? (
            <div className="text-[11px] rounded-md bg-[#ececec] dark:bg-shadeA mt-3 p-4 leading-4 relative">
              <strong>Reasoning:</strong> 
              {getReasoning(message)}
              <span
                className="absolute right-2 bottom-1 cursor-pointer"
                onClick={() => setShowResult(false)}
              >
                X
              </span>
            </div>
          ) : null}
        </div>
      )}

      {/* {message ? message : message.natural_language_response} */}
      {/* {message ? (
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
      ) : <div>The chatbot is currently down for maintenance.</div>} */}
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
