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
      if (sdata.length > 1) {
        const setresults = sdata[1]["@@edges"];
        setEdges(setresults);
        setdataArray({
          "nodes": nodez,
          "edgez": getEdgez
        })
      } else null
    }
  }, [data, sdata, edges]);

  const getNodes = edges.map((d:any) => (
    {
      "id": `${d.to_id}`,
      "label": `${d.to_id}`
    }
  ));

  const getEdgez = edges.map((d:any) => (
    {
      "source": `${d.to_id}`,
      "id": `${d.to_id}`,
      "target": '0',
      "label": `${d.e_type}`
    }
  ));

  const nodez = [
    {
      id: '0',
      label: vId
    },...getNodes
  ]

 return (
  <>
    {typeof sdata !== 'number' && typeof sdata !== 'string' && dataArray?.edgez && dataArray?.nodes ? (
      <>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[100px]">v_id</TableHead>
            <TableHead>v_type</TableHead>
            <TableHead >rlt.@count</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
            <TableRow key='0'>
              <TableCell className="font-medium">{`${sdata[0]?.rlt[0]?.attributes?.Transaction_Count}`}</TableCell>
              <TableCell>{`${sdata[0]?.rlt[0]?.v_type}`}</TableCell>
            </TableRow>
        </TableBody>
      </Table>
      </>
    ) : <div className='m-10'>Sorry no graph or table available</div> }
  </>
 )
}