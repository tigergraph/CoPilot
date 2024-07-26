import { FC, useState } from "react";
import {
  FaRegThumbsUp,
  FaThumbsUp,
  FaRegThumbsDown,
  FaThumbsDown,
} from "react-icons/fa";
import { IoMdCopy } from "react-icons/io";
import { PiArrowsCounterClockwiseFill } from "react-icons/pi";
import { Feedback, Message } from "@/actions/ActionProvider";
import { PiGraph } from "react-icons/pi";
import { FaTable } from "react-icons/fa";
import { LuInfo } from "react-icons/lu";
const COPILOT_URL = "";

interface Interactions {
  message?: any;
  showExplain: () => boolean;
  showTable: () => boolean;
  showGraph: () => boolean;
}

export const Interactions: FC<Interactions> = ({ 
  message,
  showExplain,
  showTable,
  showGraph,
}: Interactions) => {
  const [feedback, setFeedback] = useState(Feedback.NoFeedback);

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

  return (
    <div className="flex mt-3">
      {message.query_sources?.result || message.query_sources?.cypher ? (
        <>
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
            onClick={() => showExplain()}
          >
            <LuInfo className="text-[15px] mr-1" />
            <span className="text-xs">Explain</span>
          </div>

          <div className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm ml-5 mr-1 cursor-pointer" onClick={() => showGraph()}>
            <PiGraph className="text-[15px]" />
          </div>

          <div className="w-[28px] h-[28px] bg-shadeA flex items-center justify-center rounded-sm mr-1 cursor-pointer" onClick={() => showTable()}>
            <FaTable className="text-[15px]" />
          </div>

        </>
      ) : null}
    </div>
  );
}