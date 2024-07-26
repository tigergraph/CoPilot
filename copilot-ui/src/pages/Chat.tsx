import React, { useState } from "react";
import Bot from "@/components/Bot";
import SideMenu from "@/components/SideMenu";
import { RxHamburgerMenu } from "react-icons/rx";

const Chat = () => {
  const [showSidebar, setShowSidebar] = useState<boolean>(true);
  const [getConversationId, setGetConversationId] = useState<any>(['lkjh']);
  return (
    <>
      <div className="flex justify-between boxA bounce-3">
        {showSidebar ? <SideMenu setGetConversationId={setGetConversationId} /> : null}
        <div className="absolute left-0 top-0" onClick={() => setShowSidebar(prev => !prev)}><RxHamburgerMenu /></div>
        <Bot layout="fp" getConversationId={getConversationId} />
      </div>
    </>
  );
};

export default Chat;
