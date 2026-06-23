import SignInForm from "@/components/auth/SignInForm";
import { Metadata } from "next";

export const metadata: Metadata = {
  title: "feraSet Giris",
  description: "feraSet sirket paneline giris yapin.",
};

export default function SignIn() {
  return <SignInForm />;
}
