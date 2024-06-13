import React from 'react';

interface MessageParserProps{
  children: any,
  actions: any,
}

const MessageParser: React.FC<MessageParserProps> = ({ children, actions }) => {

  const parse = (message: string) => {
    actions.queryCopilotWs(message)
  };

  return (
    <div>
      {React.Children.map(children, (child) => {
        return React.cloneElement(child, {
          parse: parse,
          actions
        });
      })}
    </div>
  );
};

export default MessageParser;