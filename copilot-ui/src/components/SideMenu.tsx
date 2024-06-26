import { BsGrid } from "react-icons/bs";
import { IoDocumentTextOutline } from "react-icons/io5";
import { FiTerminal } from "react-icons/fi";
import { FiLoader } from "react-icons/fi";
import { IoCartOutline } from "react-icons/io5";
import { FiKey } from "react-icons/fi";
import { IoIosHelpCircleOutline } from "react-icons/io";
import { HiOutlineChatBubbleOvalLeft } from "react-icons/hi2";
import { MdKeyboardArrowDown } from "react-icons/md";
import { IoIosArrowForward } from "react-icons/io";
import { useTheme } from "@/components/ThemeProvider";

const SideMenu = ({ height }: { height?: string }) => {
  const getTheme = useTheme().theme;

  return (
    <div
      className={`hidden md:block w-[320px] md:min-w-[320px] overflow-y-auto ${height ? "" : "h-[100vh]"}`}
    >
      <div className="border-b border-gray-300 dark:border-[#3D3D3D] h-[70px]">
        <img
          src={
            getTheme === "dark" || getTheme === "system"
              ? "./tg-logo-bk2.svg"
              : "./tg-logo.svg"
          }
          className="min-h-[32px] pt-5 pl-5 min-w-[144px]'"
        />
      </div>

      <div className="gradient rounded-lg h-[44px] flex items-center justify-center mx-5 mt-5 text-white">
        + New Chat
      </div>

      <h1 className="Urbane-Medium text-lg pl-4 pt-5 text-black dark:text-white flex">
        <img src="./tg-logo-bk.svg" className="mr-3 ml-2" />
        <span>Chat history</span>
      </h1>
      <h4 className="Urbane-Medium text-lg pl-6 pt-5 text-black dark:text-white">
        Today
      </h4>
      <ul className="menu border-b border-gray-300 dark:border-[#3D3D3D] text-black mx-6">
        <li className="text-ellipsis">
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <HiOutlineChatBubbleOvalLeft className="text-xl mr-3" />
            How many transactions...
          </a>
        </li>
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <HiOutlineChatBubbleOvalLeft className="text-xl mr-3" />
            Describe the flow of trans..
          </a>
        </li>
      </ul>
      <h4 className="Urbane-Medium text-lg pl-6 pt-5 text-black dark:text-white">
        Yesterday
      </h4>
      <ul className="menu border-b border-gray-300 dark:border-[#3D3D3D] text-black mx-6 mb-20">
        <li className="text-ellipsis">
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <HiOutlineChatBubbleOvalLeft className="text-xl mr-3" />
            Tell me more about trans...
          </a>
        </li>
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <HiOutlineChatBubbleOvalLeft className="text-xl mr-3" />
            How transaction #8910223..
          </a>
        </li>
      </ul>
      <div
        className={`hidden md:block w-[320px] md:max-w-[320px] absolute bg-white dark:bg-background dark:border-[#3D3D3D] rounded-bl-3xl border-t ${height ? "open-dialog-avatar" : "bottom-0"}`}
      >
        <div className="flex justify-center items-center text-sm h-[80px]">
          <div>
            <img src="./avatar.svg" className="h-[42px] w-[42px] mr-4" />
          </div>
          <div className="mr-4">
            Charles P.
            <br />
            Charles.1980@gmail.com
          </div>
          <IoIosArrowForward />
        </div>
      </div>
    </div>
  );
};

export default SideMenu;
