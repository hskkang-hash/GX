import QRCodeStyling from 'qr-code-styling';

export async function generateStyledQRCode({
  data,
  logo,
  primaryColor = '#2196f3',
  width = 256,
  height = 256,
  theme = 'light',
}: {
  data: string;
  logo?: string;
  primaryColor?: string;
  width?: number;
  height?: number;
  theme?: string;
}): Promise<string> {
  const qrCode = new QRCodeStyling({
    width,
    height,
    data,
    image: logo,
    dotsOptions: {
      color: '#000',
      type: 'rounded',
    },
    cornersSquareOptions: {
      // color: primaryColor,
      type: 'extra-rounded',
    },
    backgroundOptions: {
      color: '#fff',
    },
    imageOptions: {
      crossOrigin: 'anonymous',
      margin: 2,
      imageSize: 0.2,
    },
  });

  const blob = await qrCode.getRawData('png');
  if (!blob) return '';
  return await new Promise<string>((resolve) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.readAsDataURL(blob as Blob);
  });
}
