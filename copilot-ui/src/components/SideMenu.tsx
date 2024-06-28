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
import { GoGear } from "react-icons/go";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableFooter,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { IoPencil } from "react-icons/io5";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { FaPaperclip } from "react-icons/fa6";


const SideMenu = ({ height }: { height?: string }) => {
  const getTheme = useTheme().theme;

  return (
    <div
      className={`hidden md:block w-[320px] md:min-w-[320px] overflow-y-auto ${height ? "" : "h-[100vh]"}`}
    >
      <div className="border-b border-gray-300 dark:border-[#3D3D3D] h-[70px]">
        <div className="flex items-center">
          <img
            src={
              getTheme === "dark" || getTheme === "system"
                ? "./tg-logo-bk2.svg"
                : "./tg-logo.svg"
            }
            className="min-h-[32px] pt-5 pl-5 min-w-[144px]'"
          />
          <Popover>
            <PopoverTrigger className="ml-auto"><GoGear className="text-lg mr-5 mt-4"/></PopoverTrigger>
            <PopoverContent className="flex flex-col">





            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline">Create Knowledge Graph</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[425px]">
                <DialogHeader>
                  <DialogTitle>Create Knowledge Graph</DialogTitle>
                </DialogHeader>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-4 items-center gap-4">
                    <Input
                      id="filename"
                      defaultValue="Paste a filename or url"
                      className="col-span-4"
                    />
                  </div>
                  <div className="flex mt-5"><FaPaperclip className="mr-2" /> <span>Attach file (html, pdf, txt)</span></div>
                </div>
                <DialogFooter>
                  <Button type="submit">Create</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>









            <Dialog>
              <DialogTrigger asChild>
                <Button variant="outline">Describe Graph Queries</Button>
              </DialogTrigger>
              <DialogContent className="sm:max-w-[900px]">
                <DialogHeader>
                  <DialogTitle>Describe Graph Queries</DialogTitle>
                </DialogHeader>



                {/* <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[100px]">Query Name</TableHead>
                      <TableHead className="text-right">Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                      <TableRow key='0'>
                        <TableCell className="font-medium">find_transactions_unusual_for_merchant</TableCell>
                        <TableCell className="text-right"><IoPencil/> This query reports transactions having...</TableCell>
                      </TableRow>
                  </TableBody>
                </Table> */}


                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[100px]">Query Name</TableHead>
                      <TableHead>Description</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    <TableRow>
                      <TableCell className="font-medium">find_transactions_unusual_for_merchant</TableCell>
                      <TableCell>This query reports transactions having...</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">find_transactions_unusual_for_card</TableCell>
                      <TableCell>This query reports transactions having...</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">find_transactions_unusual_velocity</TableCell>
                      <TableCell>[no description yet]</TableCell>
                    </TableRow>
                    <TableRow>
                      <TableCell className="font-medium">find_transactions_unusual_velocity</TableCell>
                      <TableCell>[no description yet]</TableCell>
                    </TableRow>
                  </TableBody>
                </Table>



                <DialogFooter>
                  <Button type="submit">Save</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>








          <Dialog>
            <DialogTrigger asChild>
              <Button variant="outline">Select LLM</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Select LLM</DialogTitle>
                <DialogDescription>
                  Please choose your AI provider and its Large Language Model. It may affect results you get.  
                </DialogDescription>
              </DialogHeader>

              <Select>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Select" />
                </SelectTrigger>
                <SelectContent>
                  <SelectGroup>
                    <SelectLabel>TBD</SelectLabel>
                  </SelectGroup>
                </SelectContent>
              </Select>

              <RadioGroup defaultValue="comfortable">
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="default" id="r1" />
                  <Label htmlFor="r1">ChatGPT-4o</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="comfortable" id="r2" />
                  <Label htmlFor="r2">ChatGPT-4</Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="compact" id="r3" />
                  <Label htmlFor="r3">ChatGPT-3.5</Label>
                </div>
              </RadioGroup>


              <DialogFooter>
                <Button type="submit">Save</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>





            </PopoverContent>
          </Popover>

        </div>
      </div>
      <h1 className="Urbane-Medium text-lg pl-5 pt-5 text-black dark:text-white">
        Menu
      </h1>
      <ul className="menu border-b border-gray-300 dark:border-[#3D3D3D] text-black mx-6">
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <BsGrid className="text-xl mr-3" /> Workgroups{" "}
            <MdKeyboardArrowDown className="text-2xl ml-auto" />
          </a>
        </li>
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <IoDocumentTextOutline className="text-xl mr-3" />
            Load Data
          </a>
        </li>
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <FiTerminal className="text-xl mr-3" /> GSQL Editor
          </a>
        </li>
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <FiLoader className="text-xl mr-3" />
            Explore Graph
          </a>
        </li>
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <IoCartOutline className="text-xl mr-3" />
            Marketplace <MdKeyboardArrowDown className="text-2xl ml-auto" />
          </a>
        </li>
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <FiKey className="text-xl mr-3" />
            Admin <MdKeyboardArrowDown className="text-2xl ml-auto" />
          </a>
        </li>
        <li>
          <a href="#" className="flex py-3 my-3 px-3 items-center">
            <IoIosHelpCircleOutline className="text-xl mr-3" />
            Help <MdKeyboardArrowDown className="text-2xl ml-auto" />
          </a>
        </li>
      </ul>
      <h1 className="Urbane-Medium text-lg pl-4 pt-5 text-black dark:text-white flex">
        <img src="./tg-logo-bk.svg" className="mr-3 ml-2" />
        <span>Copilot chat history</span>
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
            Charles.1980@gmai.com
          </div>
          <IoIosArrowForward />
        </div>
      </div>
    </div>
  );
};

export default SideMenu;
