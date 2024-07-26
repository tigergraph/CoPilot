import {useEffect, useRef, useState} from 'react';
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"

interface Post {
  id: number;
  body: string;
}

export const KnowledgeTablPro = ({ data }) => {
  const [theme, setTheme] = useState(localStorage.getItem("vite-ui-theme"));
  const ref = useRef<any | null>(null);
  const [edges, setEdges] = useState([]);
  const [dataArray, setdataArray] = useState<any>();
  const [vId, setvId] = useState<any>();


  const rowsPerPage = 10;
  // const [sdata, setData] = useState<Post[]>([]);
  const [startIndex, setStartIndex] = useState(0);
  const [endIndex, setEndIndex] = useState(rowsPerPage);


  // const getData = async () => {
  //   try {
  //     const response = await axios.get('https://jsonplaceholder.typicode.com/posts');
  //     const data = response.data;
  //     console.log(38, data);
  //     setData(data);
  //   } catch (error) {
  //     console.error('Error fetching data:', error);
  //   }
  // }
  // useEffect(() => {
  //   getData();
  // }, [])



  useEffect(() => {
    // console.log('data', data);
    if (typeof data === 'string') {
      // do i need to parse for question 'show me 5 transacitons with details'
      // const parseData = JSON.parse(data);
      // setEdges(parseData);
      // do i need to parse for question 'show me 5 transacitons with details'
      console.log('\n\n\n\n\n\n\n\n\n\n data', data);
      // console.log('\n\n\n\n\n\n\n\n\n\n PARSED STRING', parseData);
      // setEdges(parseData);
      // console.log('\n\n\n\n\n\n\n\n\n\n PARSED edges length', edges.length);
      // if (parseData.length > 0) {
      //   // YES THERE ARE 5 from question 'show me 5 transacitons with details'
      //   const setresults = parseData[1]["@@edges"];
      //   console.log('\n\n\n\n\n\n\n\n\n\n @@edges', setresults);
      //   // ^ this is valid for question 'what cards have more than 800 transactions between april 1 2021 to august 1 2021'
      //   // set the nodess and edges state here
      // } else null
    }

    if (typeof data === 'object') {
      // console.log('\n\n\n\n\n\n\n\n\n\n length', data.length);
      if (data.length > 1) {
        const setresults = data[1]["@@edges"];
        console.log('\n\n\n\n\n\n\n\n\n\n @@edges2', setresults);
        // setEdges(setresults);
        // setdataArray({
        //   "nodes": nodez,
        //   "edgez": getEdgez
        // })
      } else {
        const setresults = data["@@edges"];
        console.log('\n\n\n\n\n\n\n\n\n\n OBJECT setresults', setresults);
        setEdges(setresults);
        // THIS is a valid response for 'How do I run PageRank?'
      }
    }
  }, [data]);

  // useEffect(() => {
  //   setvId(sdata[0]?.rlt[0]?.v_id);
  //   if (typeof sdata === 'object') {
  //     if (sdata.length > 1) {
  //       const setresults = sdata[1]["@@edges"];
  //       console.log('setresults', setresults)
  //       setEdges(setresults);
  //       setdataArray({
  //         "nodes": getNodes
  //       })
  //     } else null
  //   }
  // }, [data, sdata, edges]);

  // const getNodes = edges.map((d:any) => (
  //   {
  //     "directed": `${d.directed}`,
  //     "e_type": `${d.e_type}`,
  //     "from_id": `${d.from_id}`,
  //     "from_type": `${d.from_type}`,
  //     "to_id": `${d.to_id}`,
  //     "to_type": `${d.to_type}`,
  //   }
  // ));

 return (
  <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">e_type</TableHead>
            <TableHead>from_id</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {edges.slice(startIndex, endIndex).map((item:any) => {
            return <>
              <TableRow>
                <TableCell className="text-left">{item.e_type}</TableCell>
                <TableCell className="text-left">{item.from_id}</TableCell>
              </TableRow>
            </>
          })}

        </TableBody>
      </Table>
      <Pagination>
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious
              className={
                startIndex === 0 ? "pointer-events-none opacity-50" : undefined
              }
              onClick={() => {
                setStartIndex(startIndex - rowsPerPage);
                setEndIndex(endIndex - rowsPerPage);
              }} />
          </PaginationItem>

          <PaginationItem>
            <PaginationNext
              className={
                endIndex === 100 ? "pointer-events-none opacity-50" : undefined
              }
              onClick={() => {
                setStartIndex(startIndex + rowsPerPage); //10
                setEndIndex(endIndex + rowsPerPage); //10 + 10 = 20
              }} />
          </PaginationItem>
        </PaginationContent>
      </Pagination>


    {/* {typeof data} */}
    {/* {typeof sdata !== 'number' && typeof sdata !== 'string' && dataArray?.nodes ? (
      <>
        <Tabs defaultValue="v_" className="w-[100%] text-sm lg:text-lg">
          <TabsList className="w-[100%]">
            <TabsTrigger value="v_">v_</TabsTrigger>
            <TabsTrigger value="@@edges">@@edges</TabsTrigger>
          </TabsList>
          <TabsContent value="v_">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>v_id</TableHead>
                  <TableHead>v_type</TableHead>
                  <TableHead >rlt.@count"</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                  <TableRow key='0'>
                    <TableCell>{sdata[0]?.rlt[0]?.v_id}</TableCell>
                    <TableCell>{sdata[0]?.rlt[0]?.v_type}</TableCell>
                    <TableCell>{sdata[0]?.rlt[0]?.attributes["rlt.@count"]}</TableCell>
                  </TableRow>
              </TableBody>
            </Table>
          </TabsContent>
          <TabsContent value="@@edges">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">directed</TableHead>
                  <TableHead>e_type</TableHead>
                  <TableHead >from_id</TableHead>
                  <TableHead >from_type</TableHead>
                  <TableHead >to_id</TableHead>
                  <TableHead >to_type</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dataArray?.nodes?.map((d:any) => (
                  <TableRow key='0'>
                    <TableCell>{d.directed}</TableCell>
                    <TableCell>{d.e_type}</TableCell>
                    <TableCell>{d.from_id}</TableCell>
                    <TableCell>{d.from_type}</TableCell>
                    <TableCell>{d.to_id}</TableCell>
                    <TableCell>{d.to_type}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TabsContent>
        </Tabs>
      </>
    ) : <div className='m-10'>Sorry no graph or table available</div> } */}
  </>
 )
}












// function App() {
//   const rowsPerPage = 10;
//   const [data, setData] = useState<Post[]>([]);
//   const [startIndex, setStartIndex] = useState(0);
//   const [endIndex, setEndIndex] = useState(rowsPerPage);


//   const getData = async () => {
//     try {
//       const response = await axios.get('https://jsonplaceholder.typicode.com/posts');
//       const data = response.data;
//       console.log(38, data);
//       setData(data);
//     } catch (error) {
//       console.error('Error fetching data:', error);
//     }
//   }
//   useEffect(() => {
//     getData();
//   }, [])

//   return (
//     <>
//       <Table>
//         <TableHeader>
//           <TableRow>
//             <TableHead className="w-[100px]">Id</TableHead>
//             <TableHead>Body</TableHead>
//           </TableRow>
//         </TableHeader>
//         <TableBody>
//           {data.slice(startIndex, endIndex).map((item) => {
//             return <>
//               <TableRow>
//                 <TableCell className="text-left">{item.id}</TableCell>
//                 <TableCell className="text-left">{item.body}</TableCell>
//               </TableRow>
//             </>
//           })}

//         </TableBody>
//       </Table>
//       <Pagination>
//         <PaginationContent>
//           <PaginationItem>
//             <PaginationPrevious
//               className={
//                 startIndex === 0 ? "pointer-events-none opacity-50" : undefined
//               }
//               onClick={() => {
//                 setStartIndex(startIndex - rowsPerPage);
//                 setEndIndex(endIndex - rowsPerPage);
//               }} />
//           </PaginationItem>

//           <PaginationItem>
//             <PaginationNext
//               className={
//                 endIndex === 100 ? "pointer-events-none opacity-50" : undefined
//               }
//               onClick={() => {
//                 setStartIndex(startIndex + rowsPerPage); //10
//                 setEndIndex(endIndex + rowsPerPage); //10 + 10 = 20
//               }} />
//           </PaginationItem>
//         </PaginationContent>
//       </Pagination>

//     </>
//   )
// }

// export default App
