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

export const KnowledgeTablPro = ({ data }) => {
  const [theme, setTheme] = useState(localStorage.getItem("vite-ui-theme"));
  const ref = useRef<any | null>(null);
  const [sdata, setsdata] = useState(JSON.parse(data));
  const [edges, setEdges] = useState([]);
  const [dataArray, setdataArray] = useState<any>();
  const [vId, setvId] = useState<any>();

  useEffect(() => {
    setvId(sdata[0]?.rlt[0]?.v_id);
    if (typeof sdata === 'object') {
      const rlt = {
        "v_id": sdata[0]?.rlt[0]?.v_id,
        "v_type": sdata[0]?.rlt[0]?.v_type,
        "rlt.@count": sdata[0]?.rlt[0]?.attributes?.["rlt.@count"],
      }

      if (sdata.length > 1) {
        const setresults = sdata[1]["@@edges"];
        console.log('setresults', setresults)
        setEdges(setresults);
        setdataArray({
          "nodes": getNodes,
          "rlt": rlt
        })
      } else null
    }
  }, [data, sdata, edges]);

  const getNodes = edges.map((d:any) => (
    {
      "directed": `${d.directed}`,
      "e_type": `${d.e_type}`,
      "from_id": `${d.from_id}`,
      "from_type": `${d.from_type}`,
      "to_id": `${d.to_id}`,
      "to_type": `${d.to_type}`,
    }
  ));

 return (
  <>
    {typeof sdata !== 'number' && typeof sdata !== 'string' && dataArray?.rlt && dataArray?.nodes ? (
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
                  <TableHead className="w-[100px]">v_id</TableHead>
                  <TableHead>v_type</TableHead>
                  <TableHead >rlt.@count"</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                  <TableRow key='0'>
                    <TableCell className="font-medium">{dataArray?.rlt?.v_id}</TableCell>
                    <TableCell>{dataArray?.rlt?.v_type}</TableCell>
                    <TableCell>{dataArray?.rlt?.attributes["rlt.@count"]}</TableCell>
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
                    <TableCell className="font-medium">{d.directed}</TableCell>
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
    ) : <div className='m-10'>Sorry no graph or table available</div> }
  </>
 )
}