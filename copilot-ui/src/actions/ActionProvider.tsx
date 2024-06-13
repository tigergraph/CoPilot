import React, { useState, useCallback, useEffect } from 'react';
import { createClientMessage } from 'react-chatbot-kit';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import Loader from '../components/Loader';

const API_QUERY = 'https://copilot-tg-26bfd0cd-6582-414e-937e-e2c83ecb5a79.us-east-1.i.tgcloud.io/Transaction_Fraud/query'
const WS_URL = 'ws://0.0.0.0:8000/ui/Demo_Graph1/chat';

interface ActionProviderProps {
  createChatBotMessage: any,
  setState: any,
  children: any
}

const ActionProvider: React.FC<ActionProviderProps> = ({ createChatBotMessage, setState, children }) => {

  const [socketUrl, setSocketUrl] = useState(WS_URL);
  const [messageHistory, setMessageHistory] = useState<MessageEvent<any>[]>([]);
  const { sendMessage, lastMessage, readyState } = useWebSocket(socketUrl);
  const queryCopilotWs = useCallback((msg:string) => sendMessage(msg));


  useWebSocket(WS_URL, {
    onOpen: () => {
      queryCopilotWs('dXNlcl8yOlRoaXNpc3RoZWFkbWluITE=')
      console.log('WebSocket connection established.');
    }
  });


  const updateState = (message: any) => {
    setState((prev: any) => ({
      ...prev,
      messages: [...prev.messages, message]
    }))
  }


  const defaultQuestions = (msg: string) => {
    const clientMessage = createClientMessage(msg, {
      delay: 300,
    });
    updateState(clientMessage);
    queryCopilotWs(msg);
  }


  useEffect(() => {
    if (lastMessage !== null) {
      const loading = createChatBotMessage(<Loader />)
      setState((prev: any) => ({
        ...prev,
        messages: [...prev.messages, loading]
      }));
      // setMessageHistory((prev) => prev.concat(lastMessage));
      setTimeout(() => {
        const botMessage = createChatBotMessage(JSON.parse(lastMessage.data));
        setState((prev) => {
          const newPrevMsg = prev.messages.slice(0, -1)
          return { ...prev, messages: [...newPrevMsg, botMessage], }
        })
      }, 0);
    }
  }, [lastMessage]);


  const queryCopilot = async (usrMsg: string) => {
    const settings = {
      method: 'POST',
      body: JSON.stringify({"query": usrMsg}),
      headers: {
        'Authorization': 'Basic c3VwcG9ydGFpOnN1cHBvcnRhaQ==',
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      }
    }
    const loading = createChatBotMessage(<Loader />)
    setState((prev: any) => ({
      ...prev,
      messages: [...prev.messages, loading]
    }))
    const response = await fetch(API_QUERY, settings);
    const data = await response.json();
    const botMessage = createChatBotMessage(data);
    setState((prev) => {
      const newPrevMsg = prev.messages.slice(0, -1)
      return { ...prev, messages: [...newPrevMsg, botMessage], }
    })
  }


  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Open',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Closed',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];
 
  
  return (
    <div>
      <span className='absolute bottom-0 pl-2 z-[5000] text-[8px] text-[#666]'>The WebSocket is currently {connectionStatus}</span>
      {React.Children.map(children, (child) => {
        return React.cloneElement(child, {
          actions: {
            defaultQuestions,
            queryCopilot,
            queryCopilotWs
          },
        });
      })}
    </div>
  );
};

export default ActionProvider;