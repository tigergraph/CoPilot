import React, { useState, useCallback, useEffect } from 'react';
import { createClientMessage } from 'react-chatbot-kit';
import useWebSocket, { ReadyState } from 'react-use-websocket';
import Loader from '../components/Loader';
import Loader2 from '../components/Loader2';

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
  const [showLoad, setLoad] = useState(false);


  const queryCopilotWs2 = useCallback((msg:string) => {
    sendMessage(msg);
  });


  const queryCopilotWs = ((msg:string) => {
    setLoad(true);
    sendMessage(msg)
  });


  useWebSocket(WS_URL, {
    onOpen: () => {
      queryCopilotWs2('dXNlcl8yOlRoaXNpc3RoZWFkbWluITE=')
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
    if (msg === 'Tell me about transaction fraud.') {
      console.log(msg)
      handleTransactionFraud(msg);
    } else {
      setLoad(true);
      const clientMessage = createClientMessage(msg, {
        delay: 1300,
      });
      updateState(clientMessage);
      queryCopilotWs(msg);
    }
  }

  const handleTransactionFraud = (msg) => {
    console.log(msg)
    const clientMessage = createClientMessage(msg, {
      delay: 3000,
    });
    updateState(clientMessage);
    const botMessage = createChatBotMessage('Transactions refer to the execution of a series of operations or exchanges between two or more parties. They are fundamental to various domains, particularly in economics, finance, and computer science. Here’s a detailed look at transactions in different contexts:', {
      delay: 2000,
      widget: 'transaction-fraud'
    });
    updateState(botMessage)
  }


  useEffect(() => {
    if (lastMessage !== null) {
      const loading = createChatBotMessage(<Loader />)
      setState((prev: any) => ({
        ...prev,
        messages: [...prev.messages, loading]
      }));
      setMessageHistory((prev) => prev.concat(lastMessage));
      setTimeout(() => {
        const botMessage = createChatBotMessage(JSON.parse(lastMessage.data));
        setLoad(false);
        setState((prev) => {
          const newPrevMsg = prev.messages.slice(0, -1)
          return { ...prev, messages: [...newPrevMsg, botMessage], }
        })
      }, 600);
    } 
  }, [lastMessage]);


  // const queryCopilot = async (usrMsg: string) => {
  //   const settings = {
  //     method: 'POST',
  //     body: JSON.stringify({"query": usrMsg}),
  //     headers: {
  //       'Authorization': 'Basic c3VwcG9ydGFpOnN1cHBvcnRhaQ==',
  //       'Accept': 'application/json',
  //       'Content-Type': 'application/json',
  //     }
  //   }
  //   const loading = createChatBotMessage(<Loader />)
  //   setState((prev: any) => ({
  //     ...prev,
  //     messages: [...prev.messages, loading]
  //   }))
  //   const response = await fetch(API_QUERY, settings);
  //   const data = await response.json();
  //   const botMessage = createChatBotMessage(data);
  //   setState((prev) => {
  //     const newPrevMsg = prev.messages.slice(0, -1)
  //     return { ...prev, messages: [...newPrevMsg, botMessage], }
  //   })
  // }

  const connectionStatus = {
    [ReadyState.CONNECTING]: 'Connecting',
    [ReadyState.OPEN]: 'Open',
    [ReadyState.CLOSING]: 'Closing',
    [ReadyState.CLOSED]: 'Closed',
    [ReadyState.UNINSTANTIATED]: 'Uninstantiated',
  }[readyState];
 
  
  return (
    <div>
      {/* {showLoad ? <div className='absolute bottom-[25%] right-[60%] z-[5000]'><Loader /></div> : null} */}
      {showLoad ? <div className='absolute w-[100%] h-[100%] bg-[#272022] bg-opacity-75 z-[5001]'><Loader2 /></div> : null}
      
      {/* {showLoad ? <Loader2 /> : null} */}
      <span className='absolute bottom-0 pl-2 z-[5000] text-[8px] text-[#666]'>The WebSocket is currently {connectionStatus}</span>
      {React.Children.map(children, (child) => {
        return React.cloneElement(child, {
          actions: {
            defaultQuestions,
            handleTransactionFraud,
            // queryCopilot,
            queryCopilotWs
          },
        });
      })}
    </div>
  );
};

export default ActionProvider;