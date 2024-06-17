import { FC } from "react"

interface UserAvatarProps{
  props: any
}

export const UserAvatar: FC<UserAvatarProps> = ({
  props
}) => {
  return (
    <>
      {props}
      <img src='./avatar.svg' className='h-[52px] w-[52px] relative inline-block rounded-full overflow-hidden md:h-11 md:w-11"'/>
    </>
  )
}
