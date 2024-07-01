import {useEffect, useRef, useState} from 'react';
import { GraphCanvas } from 'reagraph';

export const KnowledgeGraphPro = ({ data }) => {
  const [theme, setTheme] = useState(localStorage.getItem("vite-ui-theme"));
  const ref = useRef<any | null>(null);
  const [sdata, setsdata] = useState(JSON.parse(data));
  const [edges, setEdges] = useState([]);
  const [dataArray, setdataArray] = useState<any>();
  const [vId, setvId] = useState<any>();

  const darkTheme: any = {
    canvas: {
      // background: `${theme === "light" ? '#fff' : '#272022'}`,
      fog: '#fff'
    },
    node: {
      fill: '#F79643',
      activeFill: '#FFF',
      opacity: 1,
      selectedOpacity: 1,
      inactiveOpacity: 0.2,
      label: {
        color: '#fff',
        stroke: '#000',
        activeColor: '#F79643'
      },
      subLabel: {
        color: '#000',
        stroke: '#eee',
        activeColor: '#F79643'
      }
    },
    lasso: {
      border: '1px solid #55aaff',
      background: 'rgba(75, 160, 255, 0.1)'
    },
    ring: {
      fill: '#D8E6EA',
      activeFill: '#FFF'
    },
    edge: {
      fill: '#D8E6EA',
      activeFill: '#FFF',
      opacity: 1,
      selectedOpacity: 1,
      inactiveOpacity: 0.1,
      label: {
        stroke: '#000',
        color: '#fff',
        activeColor: '#FFF'
      }
    },
    arrow: {
      fill: '#D8E6EA',
      activeFill: '#FFF'
    },
    cluster: {
      stroke: '#D8E6EA',
      opacity: 1,
      selectedOpacity: 1,
      inactiveOpacity: 0.1,
      label: {
        stroke: '#fff',
        color: '#2A6475'
      }
    }
  };

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
      // <div className='mb-10 relative w-[92%] h-[550px]'>
        <GraphCanvas
          ref={ref} 
          nodes={dataArray?.nodes} 
          edges={dataArray?.edgez}
          labelType="all"
          theme={darkTheme}
          sizingType="centrality"
          draggable
        />
      // </div>
    ) : <div className='m-10'>Sorry no graph or table available</div> }
    {typeof sdata !== 'number' && typeof sdata !== 'string' ? (<div className='absolute top-[10px] right-[10px] w-[170px]'>
      <button className='block w-full text-right text-sm' onClick={() => ref.current?.centerGraph()}>Home</button>
    </div>) : null}
  </>
 )
}