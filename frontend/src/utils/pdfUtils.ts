import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

/**
 * Downloads the content of an HTML element as PDF
 * @param element - The HTML element to capture
 * @param filename - The filename for the downloaded PDF
 * @param options - Optional configuration for PDF generation
 */
export const downloadElementAsPDF = async (
  element: HTMLElement,
  filename: string = 'report.pdf',
  options?: {
    margin?: number;
    format?: 'a4' | 'letter';
    orientation?: 'portrait' | 'landscape';
    forceFullWidth?: boolean;
  },
): Promise<void> => {
  try {
    const margin = options?.margin ?? 10;
    const format = options?.format ?? 'a4';
    const orientation = options?.orientation ?? 'portrait';
    const forceFullWidth = options?.forceFullWidth ?? false;

    // Temporarily show element if hidden to ensure proper rendering
    const originalStyle = element.style.cssText;

    // Make element visible and properly positioned for capture
    element.style.display = 'block';
    element.style.visibility = 'visible';
    element.style.position = 'absolute';
    element.style.left = '0px';
    element.style.top = '0px';
    element.style.width = '210mm'; // A4 width in portrait
    element.style.height = 'auto';
    element.style.zIndex = '9999';
    element.style.opacity = '1';

    // Wait for element to be rendered
    await new Promise((resolve) => setTimeout(resolve, 300));

    // Create canvas from HTML element with optimized settings
    let scale = 2; // Use consistent scale for better quality
    const MAX_CANVAS_DIMENSION = 20000; // Increased limit for better quality

    // Get actual element dimensions after making it visible
    const elementWidth = element.scrollWidth || element.clientWidth || 794; // A4 width in pixels at 96 DPI
    const elementHeight = element.scrollHeight || element.clientHeight;
    const expectedWidth = elementWidth * scale;
    const expectedHeight = elementHeight * scale;

    // Reduce scale only if content is extremely large
    if (
      expectedWidth > MAX_CANVAS_DIMENSION ||
      expectedHeight > MAX_CANVAS_DIMENSION
    ) {
      const widthScale = MAX_CANVAS_DIMENSION / elementWidth;
      const heightScale = MAX_CANVAS_DIMENSION / elementHeight;
      scale = Math.min(widthScale, heightScale, scale);
      scale = Math.max(scale, 1.5); // Minimum scale for readability
    }

    const canvas = await html2canvas(element, {
      scale,
      useCORS: true,
      logging: false,
      backgroundColor: '#ffffff',
      width: elementWidth,
      height: elementHeight,
      windowWidth: elementWidth,
      windowHeight: elementHeight,
      allowTaint: false, // Must be false to allow toDataURL export
      foreignObjectRendering: false, // Disable foreign object rendering to avoid taint
    });

    // Restore original styles
    element.style.cssText = originalStyle;

    const imgWidth = canvas.width;
    const imgHeight = canvas.height;

    // Check if canvas has content
    if (imgWidth === 0 || imgHeight === 0) {
      throw new Error(
        'Canvas is empty. Element may not be visible or rendered.',
      );
    }

    // Calculate PDF dimensions
    const pdf = new jsPDF({
      orientation,
      unit: 'mm',
      format,
    });

    const pdfWidth = pdf.internal.pageSize.getWidth();
    const pdfHeight = pdf.internal.pageSize.getHeight();
    const marginMM = margin;
    const contentWidth = pdfWidth - marginMM * 2;
    const contentHeight = pdfHeight - marginMM * 2;

    // Calculate scaling to fit content
    const imgAspectRatio = imgWidth / imgHeight;
    const contentAspectRatio = contentWidth / contentHeight;

    let finalWidth: number;

    if (forceFullWidth || orientation === 'landscape') {
      // Force full width - use full content width
      finalWidth = contentWidth;
    } else if (imgAspectRatio > contentAspectRatio) {
      // Image is wider - fit to width
      finalWidth = contentWidth;
    } else {
      // Image is taller - fit to height
      finalWidth = contentHeight * imgAspectRatio;
    }

    // Calculate the corresponding height when scaled to finalWidth
    const scaledHeight = (imgHeight * finalWidth) / imgWidth;

    // Calculate number of pages needed
    const pagesNeeded = Math.ceil(scaledHeight / contentHeight);

    const yPosition = marginMM;
    let sourceY = 0;

    // Add pages and content
    for (let i = 0; i < pagesNeeded; i++) {
      if (i > 0) {
        pdf.addPage();
      }

      const remainingScaledHeight = scaledHeight - i * contentHeight;
      const pageHeight = Math.min(remainingScaledHeight, contentHeight);
      const sourceHeight = (pageHeight * imgWidth) / finalWidth;

      // Ensure sourceHeight doesn't exceed remaining canvas height
      const remainingCanvasHeight = imgHeight - sourceY;
      const actualSourceHeight = Math.min(
        Math.max(sourceHeight, 0),
        remainingCanvasHeight,
      );

      // Skip if no content to render
      if (actualSourceHeight <= 0 || remainingCanvasHeight <= 0) {
        break;
      }

      const actualPageHeight = (actualSourceHeight * finalWidth) / imgWidth;

      // Create a temporary canvas for this page
      const pageCanvas = document.createElement('canvas');
      pageCanvas.width = imgWidth;
      pageCanvas.height = actualSourceHeight;
      const pageCtx = pageCanvas.getContext('2d');

      if (pageCtx) {
        // Draw the portion of the image for this page
        pageCtx.drawImage(
          canvas,
          0,
          sourceY,
          imgWidth,
          actualSourceHeight,
          0,
          0,
          imgWidth,
          actualSourceHeight,
        );

        // Use PNG for better text quality, or JPEG with high quality
        // For text-heavy content, PNG is better even if larger
        const usePNG = actualSourceHeight < 5000; // Use PNG for smaller chunks

        let pageImgData: string;
        try {
          pageImgData = usePNG
            ? pageCanvas.toDataURL('image/png')
            : pageCanvas.toDataURL('image/jpeg', 0.92);
        } catch (error) {
          // If canvas is tainted, the original canvas from html2canvas is tainted
          // This happens when images don't have CORS headers
          // We need to re-render without cross-origin images or handle differently
          console.error(
            'Canvas is tainted. Images may be from different origin without CORS headers.',
            error,
          );
          throw new Error(
            'Cannot export PDF: Some images are from different origin without CORS headers. Please ensure all images have proper CORS configuration.',
          );
        }
        pdf.addImage(
          pageImgData,
          usePNG ? 'PNG' : 'JPEG',
          marginMM,
          yPosition,
          finalWidth,
          actualPageHeight,
        );
      }

      sourceY += actualSourceHeight;
    }

    // Save the PDF
    pdf.save(filename);
  } catch (error) {
    console.error('Error generating PDF:', error);
    throw error;
  }
};
