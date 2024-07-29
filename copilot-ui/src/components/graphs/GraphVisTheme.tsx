export const darkTheme: any = {
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