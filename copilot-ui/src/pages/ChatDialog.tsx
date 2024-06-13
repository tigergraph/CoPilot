import Bot from "../components/Bot";
import SideMenuDialog from "../components/SideMenuDialog";
import { useState } from "react";
import { RiExpandDiagonalFill } from "react-icons/ri";
import { RiCollapseDiagonalFill } from "react-icons/ri";
import { Login } from "@/components/Login";

const ChatDialog = () => {
  const [open, setOpen] = useState(false);
  const [isAuth, setIsAuth] = useState(true);
  const [chatWindow, setChatWindow] = useState<boolean>(false);

  return (
    <>
      {chatWindow ? (
        <div className={open ? 'open-dg' : ''}>
          <div className={open ? 'flex justify-between boxA bounce-3' : 'closed-dialog absolute right-10 bottom-[130px] bg-white dark:bg-background shadow-md'}>
            {isAuth ? (
              <>
                {open && <SideMenuDialog height='dg' />}
                <Bot layout={open ? 'dg' : ''} />
              </>
            ) : (
              <div className="px-10 py-10 max-w-[434px]">
                <Login setIsAuth={setIsAuth} />
              </div>
            )}
          </div>
        </div>
      ) : null}

      <div id='circle'
           className='absolute right-7 bottom-7 button-image bg-[#50d71e]'
           onClick={() => setChatWindow(showChat => !showChat)}>
           {chatWindow ? 'X' : <img src="./white-tg-logo.svg" />}
      </div>

      {chatWindow && isAuth && <div
        id='expand'
        className='absolute right-[105px] bottom-7 button-image bg-[#fff]'
        onClick={() => setOpen(prev => !prev)}
      >
        {open ? (
          <>
            <span>Collapse</span> <RiCollapseDiagonalFill className="ml-1 text-xl" />
          </>
        ) : (
          <>
            <span>Expand</span> <RiExpandDiagonalFill className="ml-1 text-xl" />
          </>
        )}
      </div>}

      <div className="back-drop"></div>
    </>
  );
};

export default ChatDialog;


