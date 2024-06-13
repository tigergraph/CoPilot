import Bot from "@/components/Bot";
import SideMenu from "@/components/SideMenu";

const Chat = () => {
  return (
    <>
      <div className="flex justify-between boxA bounce-3">
        <SideMenu />
        <Bot layout='fp'/>
      </div>
    </>
  );
};

export default Chat;
