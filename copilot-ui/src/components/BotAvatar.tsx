interface BotAvatarProps{
    props: any
}


export const BotAvatar: React.FC<BotAvatarProps> = ({
    props
}) => {
  return (
    <div>{props}
      <img src="/chat-tg-logo.svg" alt="" className="relative inline-block rounded-full overflow-hidden h-12 w-[52px] mr-3 pt-1 mt-3"/>
    </div>
  )
}
