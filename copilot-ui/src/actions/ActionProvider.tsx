import React, {useState, useCallback, useEffect} from 'react';
import {createClientMessage} from 'react-chatbot-kit';
import useWebSocket, {ReadyState} from 'react-use-websocket';
import Loader from '../components/Loader';


const WS_URL = "/ui/Transaction_Fraud/chat";

interface ActionProviderProps {
  createChatBotMessage: any;
  setState: any;
  children: any;
}

export enum Feedback {
  NoFeedback = 0,
  LIKE,
  DISLIKE,
}
export interface Message {
  conversationId: string;
  messageId: string;
  parentId: string;
  modelName: string;
  content: string;
  answered_question: boolean;
  response_type: string;
  query_sources: any;
  role: string;
  feedback: Feedback;
  comment: string;
}

const ActionProvider: React.FC<ActionProviderProps> = ({
  createChatBotMessage,
  setState,
  children,
}) => {
  const [socketUrl, setSocketUrl] = useState(WS_URL);
  const [messageHistory, setMessageHistory] = useState<MessageEvent<Message>[]>([]);
  const {sendMessage, lastMessage, readyState} = useWebSocket(socketUrl);

  // eslint-disable-next-line
  // @ts-ignore
  const queryCopilotWs2 = useCallback((msg: string) => {
    sendMessage(msg);
  });

  useWebSocket(WS_URL, {
    onOpen: () => {
      queryCopilotWs2(localStorage.getItem("creds")!);
      console.log("WebSocket connection established.");
    },
  });

  const updateState = (message: any) => {
    setState((prev: any) => ({
      ...prev,
      messages: [...prev.messages, message],
    }));
  };

  const defaultQuestions = (msg: string) => {
    if (msg === 'Tell me about transaction fraud.') {
      handleTransactionFraud(msg);
    } else {
      const clientMessage = createClientMessage(msg, {
        delay: 300,
      });
      updateState(clientMessage);
      queryCopilotWs(msg);
    }
  };

  const queryCopilotWs = (msg) => {
    const queryCopilotWsTest = (msg: string) => {
      sendMessage(msg);
    };
    queryCopilotWsTest(msg);
    const loading = createChatBotMessage(<Loader />);
    setState((prev: any) => ({
      ...prev,
      messages: [...prev.messages, loading],
    }));
  };

  const handleTransactionFraud = (msg) => {
    console.log(msg);
    const clientMessage = createClientMessage(msg, {
      delay: 3000,
    });
    updateState(clientMessage);
    const loading = createChatBotMessage(<Loader />);
    setState((prev: any) => ({
      ...prev,
      messages: [...prev.messages, loading],
    }));
    setTimeout(() => {
      const botMessage = createChatBotMessage(
        'Transactions refer to the execution of a series of operations or exchanges between two or more parties. They are fundamental to various domains, particularly in economics, finance, and computer science. Here’s a detailed look at transactions in different contexts:',
        {
          delay: 0,
          widget: 'transaction-fraud',
        }
      );
      setState((prev) => {
        const newPrevMsg = prev.messages.slice(0, -1);
        return {...prev, messages: [...newPrevMsg, botMessage]};    
      });
    }, 2000);
  };

  useEffect(() => {
    if (lastMessage !== null) {
      setMessageHistory((prev) => prev.concat(lastMessage));
      const botMessage = createChatBotMessage(JSON.parse(lastMessage.data));
      console.log(botMessage.message);
      setState((prev) => {
        const newPrevMsg = prev.messages.slice(0, -1);
        return {...prev, messages: [...newPrevMsg, botMessage]};  
      });
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
      <span className='absolute bottom-0 pl-2 z-[5000] text-[8px] text-[#666]'>The WebSocket is currently {connectionStatus}</span>
      {React.Children.map(children, (child) => {
        return React.cloneElement(child, {
          actions: {
            defaultQuestions,
            handleTransactionFraud,
            queryCopilotWs,
          },
        });
      })}
    </div>
  );
};

export default ActionProvider;
