import {useRef} from 'react';
import { GraphCanvas } from 'reagraph';

export const darkTheme: any = {
  canvas: {
    background: '#272022',
    fog: '#fff'
  },
  node: {
    fill: '#7CA0AB',
    activeFill: '#1DE9AC',
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.2,
    label: {
      color: '#2A6475',
      stroke: '#fff',
      activeColor: '#1DE9AC'
    },
    subLabel: {
      color: '#2A6475',
      stroke: '#eee',
      activeColor: '#1DE9AC'
    }
  },
  lasso: {
    border: '1px solid #55aaff',
    background: 'rgba(75, 160, 255, 0.1)'
  },
  ring: {
    fill: '#D8E6EA',
    activeFill: '#1DE9AC'
  },
  edge: {
    fill: '#D8E6EA',
    activeFill: '#1DE9AC',
    opacity: 1,
    selectedOpacity: 1,
    inactiveOpacity: 0.1,
    label: {
      stroke: '#fff',
      color: '#2A6475',
      activeColor: '#1DE9AC'
    }
  },
  arrow: {
    fill: '#D8E6EA',
    activeFill: '#1DE9AC'
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

export const KnowledgeGraph = ({ data }) => {
  const ref = useRef<any | null>(null);

  return (
    <>
    {data ? (
      <GraphCanvas
        ref={ref} 
        nodes={data.nodes} 
        edges={data.edgez}
        labelType="all"
        theme={darkTheme}
        sizingType="centrality"
        draggable
      />
    ) : '...loading'}

    <div className='absolute top-0 right-0 w-[200px]'>
      <button className='block w-full' onClick={() => ref.current?.centerGraph()}>Center</button>
      <button className='block w-full' onClick={() => ref.current?.centerGraph([data.nodes[2].id])}>Center Node 2</button>
      <button className='block w-full' onClick={() => ref.current?.fitNodesInView()}>Fit View</button>
      <br />
      <button className='block w-full' onClick={() => ref.current?.zoomIn()}>Zoom In</button>
      <button className='block w-full' onClick={() => ref.current?.zoomOut()}>Zoom Out</button>
      <button className='block w-full' onClick={() => ref.current?.dollyIn()}>Dolly In</button>
      <button className='block w-full' onClick={() => ref.current?.dollyOut()}>Dolly Out</button>
      <br />
      <button className='block w-full' onClick={() => ref.current?.panDown()}>Pan Down</button>
      <button className='block w-full' onClick={() => ref.current?.panUp()}>Pan Up</button>
      <button className='block w-full' onClick={() => ref.current?.panLeft()}>Pan Left</button>
      <button className='block w-full' onClick={() => ref.current?.panRight()}>Pan Right</button>
    </div>

  {/* <div style={{
      position: 'absolute',
      top: 0,
      bottom: 0,
      left: 0,
      right: 0
    }}>
      <div style={{
        zIndex: 1,
        position: 'absolute',
        top: 15,
        right: 15,
        background: 'rgba(0, 0, 0, .5)',
        padding: 1,
        color: 'white'
      }}>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.centerGraph()}>Center</button>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.centerGraph([simpleNodes[2].id])}>Center Node 2</button>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.fitNodesInView()}>Fit View</button>
          <br />
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.zoomIn()}>Zoom In</button>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.zoomOut()}>Zoom Out</button>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.dollyIn()}>Dolly In</button>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.dollyOut()}>Dolly Out</button>
          <br />
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.panDown()}>Pan Down</button>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.panUp()}>Pan Up</button>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.panLeft()}>Pan Left</button>
          <button style={{
          display: 'block',
          width: '100%'
        }} onClick={() => ref.current?.panRight()}>Pan Right</button>
        </div>
        {JSON.stringify(data, null, 2)}
        <GraphCanvas
          ref={ref} 
          nodes={data.nodes} 
          edges={data.edgez}
          labelType="all"
          theme={darkTheme}
          sizingType="centrality"
          draggable
        />
      </div> */}
    </>
  )
}