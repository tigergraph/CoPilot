import { createCustomMessage } from 'react-chatbot-kit';
import { BotAvatar } from '../components/BotAvatar';
import { UserAvatar } from '../components/UserAvatar';
import { CustomChatMessage } from '../components/CustomChatMessage';
import { Start } from '../components/Start';
import CustomMessage from '../components/CustomMessage';


const config = {
  initialMessages: [
    createCustomMessage('Test', 'custom', { widget: 'overview' })
  ],

  customMessages: {
    custom: (props) => <CustomMessage {...props} />,
  },

  widgets: [
    {
      widgetName: 'overview',
      widgetFunc: (props: any) => <Start {...props}  />,
      mapStateToProps: ["messages"]
    }
  ],

  customStyles:{
    botMessageBox: {
      backgroundColor: '#8B5CF6'
    }
  },

  customComponents: {
    header: () => <div></div>,
    botChatMessage: (props: any) => <CustomChatMessage {...props}/>,
    botAvatar: (props: any) => <BotAvatar {...props}/>,
    userAvatar: (props: any) => <UserAvatar {...props}/>
  }

  // Defines an object of custom components that will replace the stock chatbot components. 
  //   customComponents: {
  //     // Replaces the default header
  //    header: () => <div style={{ backgroundColor: 'red', padding: "5px", borderRadius: "3px" }}>This is the header</div>
  //    // Replaces the default bot avatar
  //    botAvatar: (props) => <FlightBotAvatar {...props} />,
  //    // Replaces the default bot chat message container
  //    botChatMessage: (props) => <CustomChatMessage {...props} />,
  //    // Replaces the default user icon
  //    userAvatar: (props) => <MyUserAvatar {...props} />,
  //    // Replaces the default user chat message
  //    userChatMessage: (props) => <MyUserChatMessage {...props} />
  //  },
};

export default config;