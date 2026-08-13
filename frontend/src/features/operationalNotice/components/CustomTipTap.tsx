import { DownOutlined } from '@ant-design/icons';
import { Extension } from '@tiptap/core';
import Color from '@tiptap/extension-color';
import Document from '@tiptap/extension-document';
import HardBreak from '@tiptap/extension-hard-break';
import Heading from '@tiptap/extension-heading';
import Highlight from '@tiptap/extension-highlight';
import HorizontalRule from '@tiptap/extension-horizontal-rule';
import Paragraph from '@tiptap/extension-paragraph';
import Table from '@tiptap/extension-table';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import TableRow from '@tiptap/extension-table-row';
import Text from '@tiptap/extension-text';
import TextAlign from '@tiptap/extension-text-align';
import TextStyle from '@tiptap/extension-text-style';
import Underline from '@tiptap/extension-underline';
import { EditorContent, useEditor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import { ColorPicker, ConfigProvider, Select } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
// Import icons
import { BsCodeSquare, BsFileBreak, BsTrash } from 'react-icons/bs';
import {
  FaAlignCenter,
  FaAlignLeft,
  FaAlignRight,
  FaBold,
  FaBorderNone,
  FaCode,
  FaImage,
  FaItalic,
  FaListOl,
  FaListUl,
  FaObjectGroup,
  FaObjectUngroup,
  FaPrint,
  FaRedo,
  FaRulerHorizontal,
  FaStrikethrough,
  FaTable,
  FaUnderline,
  FaUndo,
} from 'react-icons/fa';
import {
  MdArrowBack,
  MdArrowDownward,
  MdArrowForward,
  MdArrowUpward,
  MdFormatColorText,
  MdOutlineDeleteOutline,
  MdOutlineTableRows,
  MdOutlineViewHeadline,
} from 'react-icons/md';
import { TbH1, TbH2, TbH3, TbH4, TbH5, TbH6 } from 'react-icons/tb';
import { useReactToPrint } from 'react-to-print';
import { useTheme } from 'rj-core';
import ImageResize from 'tiptap-extension-resize-image';

import '../../reportTemplate/assets/style/CustomTipTap.scss';
import { FontSize } from '../hooks/FontSize';
import {
  CustomTiptapProps,
  OperationalNoticeFormValues,
} from '../types/operationalNotice.types';

// Custom extension to preserve class attributes
const PreserveClassExtension = Extension.create({
  name: 'preserveClass',

  addGlobalAttributes() {
    return [
      {
        types: [
          'paragraph',
          'heading',
          'listItem',
          'table',
          'tableRow',
          'tableCell',
          'tableHeader',
        ],
        attributes: {
          class: {
            default: null,
            parseHTML: (element) => element.getAttribute('class'),
            renderHTML: (attributes) => {
              if (!attributes.class) {
                return {};
              }
              return {
                class: attributes.class,
              };
            },
          },
        },
      },
    ];
  },
});

export const CustomTiptap: React.FC<CustomTiptapProps> = ({
  content = '',
  onChange,
  label,
  heightContent = '500px',
  includeStyles = false,
  // fieldsTemplate,
}) => {
  const { t } = useTranslation();

  const [theme] = useTheme();
  const [openFontColorPicker, setOpenFontColorPicker] = useState(false);
  const [openBackgroundPicker, setOpenBackgroundPicker] = useState(false);
  const [openContentBackgroundPicker, setOpenContentBackgroundPicker] =
    useState(false);
  const [isTableBorderVisible, setIsTableBorderVisible] = useState(false);
  const [isRowHeaderActive, setIsRowHeaderActive] = useState(false);
  const [localContent, setLocalContent] = useState(content);
  const [contentBackgroundColor, setContentBackgroundColor] = useState(
    'transparent !important',
  );
  const [isUpdatingFromProps, setIsUpdatingFromProps] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const printRef = useRef<HTMLDivElement>(null);

  const handlePrint = useReactToPrint({
    contentRef: printRef,
    documentTitle: 'TipTap Content',
  });

  const contentStyles = `
  .tiptap-preview h1,
  .tiptap-preview h2,
  .tiptap-preview h3,
  .tiptap-preview h4,
  .tiptap-preview h5,
  .tiptap-preview h6 {
  font-weight: bold;
  line-height: 1.5;
  overflow-wrap: break-word;
  page-break-inside: avoid;
  break-inside: avoid;
  text-wrap: balance;
  }

  .tiptap-preview h1 {
  font-size: 2.5rem;
  }

  .tiptap-preview h2 {
  font-size: 2rem;
  }

  .tiptap-preview h3 {
  font-size: 1.75rem;
  }

  .tiptap-preview h4 {
  font-size: 1.5rem;
  }

  .tiptap-preview h5 {
  font-size: 1.25rem;
  }

  .tiptap-preview h6 {
  font-size: 1rem;
  }


  .tiptap-preview p {
  margin: 0.5rem 0;
  font-size: 1.25rem;
  overflow-wrap: break-word;
  -webkit-user-modify: read-write-plaintext-only;
  }

  .tiptap-preview ul, .tiptap-preview ol {
  padding: 0 1rem;
  margin: 0.5rem 0;
  }

  .tiptap-preview ul li, .tiptap-preview ol li {
  padding: 0.2em 0;
  }

  .tiptap-preview ul li p, .tiptap-preview ol li p {
  margin: 0.25em 0;
  }

  .tiptap-preview table {
  border-collapse: collapse;
  margin: 0.5rem 0;
  overflow: hidden;
  table-layout: fixed;
  width: 100%;

  &.hide-table-borders > tbody > tr > td {
  border: none;
  }
  }

  .tiptap-preview table td, .tiptap-preview table th {
  border: 1px solid ${theme === 'dark' ? '#495057' : '#ced4da'};
  padding: 3px 5px;
  vertical-align: top;
  box-sizing: border-box;
  min-width: 1em;
  position: relative;


  }

  .tiptap-preview table td p, .tiptap-preview table th p {
  margin: 0;
  overflow-wrap: break-word;
  -webkit-user-modify: read-write-plaintext-only;
  }

  .tiptap-preview table th {
  background-color: ${theme === 'dark' ? '#212529' : '#f1f3f5'};
  font-weight: bold;
  text-align: left;
  }

  .tiptap-preview table td > *, .tiptap-preview table th > * {
  margin-bottom: 0;
  }

  .tiptap-preview blockquote {
  border-left: 3px solid #f2f2f2;
  margin: 0.5rem 0;
  padding-left: 1rem;
  }

  .tiptap-preview code {
  border-radius: 4px;
  color: ${theme === 'dark' ? '#e9ecef' : '#212529'};
  font-size: 0.85rem;
  font-family: 'JetBrainsMono', monospace;
  padding: 0.25em 0.3em;
  }

  .tiptap-preview pre {
  font-family: 'JetBrainsMono', monospace;
  border-radius: 0.5rem;
  margin: 0.5rem 0;
  padding: 0.75rem 1rem;
  overflow-x: auto;
  }

  .tiptap-preview pre code {
  background: none;
  color: inherit;
  font-size: 0.8rem;
  padding: 0;
  }

  .tiptap-preview hr {
  border: none;
  border-top: 1px solid ${theme === 'dark' ? '#ced4da' : '#ced4da'};
  margin: 0.5rem 0;
  }

  .tiptap-preview a {
  color: #4a6cfa;
  text-decoration: underline;
  }

  .tiptap-preview a:hover {
  text-decoration: none;
  }

  .tiptap-preview img {
  max-width: 100%;
  height: auto;
  cursor: pointer;
  }

  .tiptap-preview .image-wrapper {
  display: flex;
  }

  .tiptap-preview .code-block-wrapper {
  padding: 0 !important;
  background-color: transparent !important;
  }


  .hide-table-borders > tbody > tr > td {
  border: none;
  }

  .report-container {
  width: 100%;
  margin: 0 auto;
  /*border: 2px solid #000;*/
  }

  .header-tel {
  text-align: right;
  font-size: 8px;
  }

  .header-text {
  flex: 1;
  }

  .title-section {
  margin: 1px;
  display: flex;
  align-items: center;
  padding: 10px 15px;
  }

  .main-title {
  font-size: 18px;
  font-weight: bold;
  flex: 1;
  }

  .approval-table {
  border: 2px solid #000;
  border-collapse: collapse;
  }

  .approval-table td {
  border: 1px solid #000;
  padding: 4px 10px;
  text-align: center;
  font-size: 8px;
  width: 40px;
  height: 20px;
  }

  .approval-table .signature-row td {
  height: 30px;
  }

  .basic-info {
  width: 100%, padding: 10px 15px;
  /*border-bottom: 1px solid #000;*/
  }

  .info-line {
  margin-bottom: 4px;
  font-size: 8px;
  }

  .black-header {
  color: black;
  padding: 4px 12px;
  font-weight: bold;
  font-size: 9px;
  }

  .horizal-divider {
  background: #fff;
  height: 1px;
  border: 2px solid #000;
  border-left-width: 0;
  border-right-width: 0;
  }

  .flight-status {
  width: 100%, display: flex;
  min-height: 120px;
  }

  .left-content {
  flex: 1;
  padding: 10px 15px;
  }

  .right-content {
  display: flex;
  flex-direction: row;
  gap: 10px;
  margin-bottom: 5px;
  justify-content: center;
  }

  .status-line {
  display: flex;
  margin-bottom: 3px;
  font-size: 8px;
  }

  .status-bullet {
  width: 12px;
  }

  .status-label {
  width: 40px;
  font-weight: bold;
  }

  .diagonal-box {
  position: absolute;
  right: 15px;
  top: 15px;
  width: 150px;
  height: 80px;
  border: 1px solid #000;
  background-image: repeating-linear-gradient(45deg, transparent, transparent 4px, #000 4px, #000 5px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  }

  .diagonal-text {
  background: white;
  padding: 2px 6px;
  font-size: 7px;
  text-align: center;
  margin: 2px;
  }

  .gray-header {
  background: #808080;
  color: white;
  padding: 4px 12px;
  font-weight: bold;
  font-size: 9px;
  margin: 4px 0px 0px 0px;
  }

  .checklist-table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  table-layout: auto;
  }

  .checklist-table td {
  border: 1px solid #000;
  padding: 3px 8px;
  font-size: 8px;
  vertical-align: top;
  word-wrap: break-word;
  overflow-wrap: break-word;
  }

  .auto-check-header {
  background: #808080;
  color: white;
  font-weight: bold;
  text-align: center;
  min-width: 150px;
  font-size: 14px !important;
  }

  .status-header {
  background: #808080;
  color: white;
  font-weight: bold;
  text-align: center;
  min-width: 80px;
  font-size: 14px !important;
  }

  .check-item {
  min-width: 150px;
  max-width: 200px;
  }

  .status-cell {
  min-width: 80px;
  max-width: 100px;
  }

  .action-cell {
  min-width: 80px;
  max-width: 100px;
  font-size: 7px;
  }

  .section-header {
  background: #c0c0c0;
  font-weight: bold;
  text-align: center;
  font-size: 14px !important;
  min-width: 150px;
  }

  .sub-header {
  background: #c0c0c0;
  font-weight: bold;
  text-align: center;
  }

  .inspection-section {
  display: flex;
  }

  .inspection-left {
  width: 50%;
  border-right: 1px solid #000;
  }

  .inspection-right {
  width: 50%;
  }

  .inspection-category {
  background: #c0c0c0;
  padding: 3px 8px;
  font-weight: bold;
  font-size: 8px;
  border-bottom: 1px solid #000;
  }

  .inspection-item {
  padding: 3px 8px;
  font-size: 7px;
  border-bottom: 1px solid #ddd;
  min-height: 16px;
  }

  .item-bullet {
  margin-right: 4px;
  }

  .inner-table {
  width: 100%;
  border-collapse: collapse;
  /* viền dính nhau */
  }

  .inner-table td {
  border: 1px solid #000;
  padding: 3px 8px;
  font-size: 8px;
  }

  .title-checklist {
  display: flex;
  padding: 0px 0px 3px 0px;
  }

  .title-left,
  .title-right {
  flex: 1;
  font-weight: bold;
  font-size: 9px;
  }

  .image-box {
  width: 25%;
  display: flex;
  align-items: center;
  justify-content: center;
  }

  .image-box img {
  max-width: 100%;
  max-height: auto;
  object-fit: contain;
  }
  `;

  const editor = useEditor({
    content,
    parseOptions: {
      preserveWhitespace: 'full',
    },
    editorProps: {
      attributes: {
        class: 'tiptap-editor-content',
      },
    },
    extensions: [
      StarterKit,
      ImageResize.configure({
        allowBase64: true,
      }),
      Underline,
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
      HorizontalRule,
      HardBreak,
      TextStyle,
      Color,
      Highlight.configure({
        multicolor: true,
      }),
      TextAlign.configure({
        types: ['heading', 'paragraph'],
      }),
      Document,
      Paragraph,
      Text,
      Heading,
      FontSize,
      PreserveClassExtension,
    ],
    onUpdate({ editor }) {
      if (onChange && !isUpdatingFromProps) {
        // Use DOM innerHTML to preserve all classes and attributes
        const editorContent = editor.view.dom.innerHTML;
        console.log('editor_operational_notice', contentBackgroundColor);
        let editorHTML = `<div class="tiptap-preview"><div style="background-color: ${contentBackgroundColor}; padding: 4px;border-radius: 8px;">${editorContent}</div></div>`;

        editorHTML = editorHTML.replace(
          /<img([^>]*)>/g,
          '<div class="image-wrapper"><img$1></div>',
        );
        if (includeStyles) {
          editorHTML = `<style>${contentStyles}</style>${editorHTML}`;
        }
        console.log('editorHTML', editorHTML);
        setLocalContent(editorHTML);
        onChange(editorHTML);
      }
    },
    onSelectionUpdate({ editor }) {
      const isHeader = editor.isActive('tableHeader');
      setIsRowHeaderActive(isHeader);

      const isInTable = editor.isActive('table');

      if (isInTable) {
        const { selection } = editor.state;
        const { $from } = selection;

        const editorElement = document.querySelector('.tiptap-editor');
        const domAtPos = editor.view.domAtPos($from.pos);
        let current = domAtPos.node;

        while (current && current !== editorElement) {
          if (current.nodeName === 'TABLE') {
            const currentTable = current as HTMLTableElement;
            const isTableHidden =
              currentTable.classList.contains('hide-table-borders');
            setIsTableBorderVisible(isTableHidden);
            return;
          }
          current = current?.parentNode as Node;
        }
      }
    },
  });

  useEffect(() => {
    if (editor && content !== localContent) {
      // Only update content if it's actually different from what's in the editor
      const currentEditorContent = editor.getHTML();
      const cleanContent = content.replace(
        /<div class="tiptap-preview"><div[^>]*>(.*?)<\/div><\/div>/s,
        '$1',
      );

      if (currentEditorContent !== cleanContent) {
        // Set flag to prevent onUpdate from triggering
        setIsUpdatingFromProps(true);

        // Preserve selection and formatting when updating content
        const { from, to } = editor.state.selection;
        const hasSelection = from !== to;

        editor.commands.setContent(content, false);

        // Only restore selection if there was a selection before
        if (
          hasSelection &&
          from < editor.state.doc.content.size &&
          to <= editor.state.doc.content.size
        ) {
          editor.commands.setTextSelection({ from, to });
        }

        // Reset flag after a short delay
        setTimeout(() => setIsUpdatingFromProps(false), 100);
      }
      setLocalContent(content);
    }
  }, [content, editor, localContent]);

  // // Extract and sync background color when content changes (tab switching)
  // useEffect(() => {
  //   if (content) {
  //     // Look for background-color in the main wrapper div
  //     const backgroundColorMatch = content.match(
  //       /<div[^>]*style="[^"]*background-color:\s*([^;"]+)[^"]*"[^>]*>/,
  //     );
  //     if (backgroundColorMatch) {
  //       const extractedColor = backgroundColorMatch[1].trim();
  //       if (extractedColor !== contentBackgroundColor) {
  //         setContentBackgroundColor(extractedColor);
  //       }
  //     } else {
  //       // If content doesn't have background color or is empty, reset to default white
  //       // This ensures each tab starts with white background unless explicitly set
  //       if (contentBackgroundColor !== '#ffffff') {
  //         setContentBackgroundColor('#ffffff');
  //       }
  //     }
  //   } else {
  //     // If content is empty or null, reset to default white
  //     if (contentBackgroundColor !== '#ffffff') {
  //       setContentBackgroundColor('#ffffff');
  //     }
  //   }
  // }, [content]); // Only depend on content, not contentBackgroundColor

  // Update preview when contentBackgroundColor changes
  useEffect(() => {
    if (editor && onChange) {
      setIsUpdatingFromProps(true);
      console.log('contentBackgroundColor', contentBackgroundColor);
      const editorContent = editor.view.dom.innerHTML;
      let editorHTML = `<div class="tiptap-preview"><div style="background-color: ${contentBackgroundColor}; padding: 6px;border-radius: 8px;">${editorContent}</div></div>`;

      editorHTML = editorHTML.replace(
        /<img([^>]*)>/g,
        '<div class="image-wrapper"><img$1></div>',
      );

      if (includeStyles) {
        editorHTML = `<style>${contentStyles}</style>${editorHTML}`;
      }

      setLocalContent(editorHTML);
      onChange(editorHTML);

      // Reset flag after a short delay
      setTimeout(() => setIsUpdatingFromProps(false), 100);
    }
  }, [contentBackgroundColor, editor, includeStyles]); // eslint-disable-line react-hooks/exhaustive-deps

  const toggleTableBorders = (): void => {
    // Kiểm tra xem cursor có đang ở trong table không
    if (!editor || !editor.isActive('table')) {
      return;
    }

    // Tìm table element chứa cursor hiện tại
    const { selection } = editor.state;
    const { $from } = selection;

    // Tìm table DOM element tương ứng
    const editorElement = document.querySelector('.tiptap-editor');
    const domAtPos = editor.view.domAtPos($from.pos);
    let current = domAtPos.node;

    // Traverse up để tìm table element
    while (current && current !== editorElement) {
      if (current.nodeName === 'TABLE') {
        const currentTableElement = current as HTMLTableElement;

        // Kiểm tra trạng thái hiện tại
        const hasHiddenBorders =
          currentTableElement.classList.contains('hide-table-borders');

        // Toggle border chỉ cho table hiện tại
        if (hasHiddenBorders) {
          currentTableElement.classList.remove('hide-table-borders');
          setIsTableBorderVisible(true); // Border giờ đã visible
        } else {
          currentTableElement.classList.add('hide-table-borders');
          setIsTableBorderVisible(false); // Border giờ bị hide
        }

        // Manually call onChange with updated content
        if (onChange) {
          setIsUpdatingFromProps(true);

          const editorContent = editor.view.dom.innerHTML;
          let html = `<div class="tiptap-preview"><div style="background-color: ${contentBackgroundColor}; padding: 6px;border-radius: 8px;">${editorContent}</div></div>`;

          html = html.replace(
            /<img([^>]*)>/g,
            '<div class="image-wrapper"><img$1></div>',
          );

          if (includeStyles) {
            html = `<style>${contentStyles}</style>${html}`;
          }
          setLocalContent(html);
          onChange(html);

          // Reset flag after a short delay
          setTimeout(() => setIsUpdatingFromProps(false), 100);
        }

        return;
      }
      current = current?.parentNode as Node;
    }
  };

  const toggleRowHeader = () => {
    if (!editor) return;

    // First make sure we're inside a table
    if (!editor.isActive('table')) return;

    // Toggle the selected row between header and normal
    editor.chain().focus().toggleHeaderRow().run();
  };

  const addImage = () => {
    if (fileInputRef.current) {
      // User chose to upload from computer
      fileInputRef.current.click();
    } else {
      // User chose to enter a URL
      const url = prompt('Enter the URL of the image:');

      if (url && editor) {
        editor.chain().focus().setImage({ src: url }).run();
      }
    }
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file || !editor) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      const result = e.target?.result;
      if (result && typeof result === 'string') {
        editor.chain().focus().setImage({ src: result }).run();
      }
    };
    reader.readAsDataURL(file);

    // Reset the file input so the same file can be selected again if needed
    event.target.value = '';
  };

  if (!editor) return null;

  return (
    <div
      className="tiptap-container"
      data-bs-theme={theme}
      style={{ height: heightContent }}
    >
      {/* Hidden file input for image uploads */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: 'none' }}
        accept="image/*"
        onChange={handleFileUpload}
      />

      <div className="tiptap-wrapper">
        {label && <div className="tiptap-label">{label}</div>}

        <div className="tiptap-toolbar">
          <div className="toolbar-group">
            <button
              className={editor.isActive('bold') ? 'is-active' : ''}
              onClick={() => editor.chain().focus().toggleBold().run()}
              title="Bold"
              type="button"
            >
              <FaBold />
            </button>
            <button
              className={editor.isActive('italic') ? 'is-active' : ''}
              onClick={() => editor.chain().focus().toggleItalic().run()}
              title="Italic"
              type="button"
            >
              <FaItalic />
            </button>
            <button
              className={editor.isActive('underline') ? 'is-active' : ''}
              onClick={() => editor.chain().focus().toggleUnderline().run()}
              title="Underline"
              type="button"
            >
              <FaUnderline />
            </button>
            <button
              className={editor.isActive('strike') ? 'is-active' : ''}
              onClick={() => editor.chain().focus().toggleStrike().run()}
              title="Strike"
              type="button"
            >
              <FaStrikethrough />
            </button>
          </div>

          <div className="toolbar-divider"></div>

          <div className="toolbar-group">
            <ColorPicker
              open={openFontColorPicker}
              onOpenChange={setOpenFontColorPicker}
              onChange={(color) =>
                editor.chain().focus().setColor(color.toHexString()).run()
              }
            >
              <span
                className="px-2"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  cursor: 'pointer',
                }}
              >
                <MdFormatColorText
                  color={
                    editor.getAttributes('textStyle').color ||
                    (theme === 'dark' ? '#ffffff' : '#000000')
                  }
                  size={20}
                />
                <DownOutlined rotate={openFontColorPicker ? 180 : 0} />
              </span>
            </ColorPicker>

            <ColorPicker
              defaultValue="#ffffff"
              open={openBackgroundPicker}
              onOpenChange={setOpenBackgroundPicker}
              onChange={(color) => {
                const hex = color.toHexString();
                editor.chain().focus().setHighlight({ color: hex }).run();
              }}
            >
              <div
                className="px-2"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  cursor: 'pointer',
                }}
              >
                <div
                  style={{
                    width: '1.25rem',
                    height: '1.25rem',
                    backgroundColor: editor.getAttributes('highlight').color,
                    border: '1px solid #ccc',
                    borderRadius: '0.125rem',
                  }}
                />
                <DownOutlined rotate={openBackgroundPicker ? 180 : 0} />
              </div>
            </ColorPicker>

            {/* Content Background Color */}
            <ColorPicker
              value={contentBackgroundColor}
              open={openContentBackgroundPicker}
              onOpenChange={setOpenContentBackgroundPicker}
              onChange={(color) => {
                const hex = color.toHexString();
                setContentBackgroundColor(hex);
              }}
            >
              <div
                className="px-2"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  cursor: 'pointer',
                }}
                title="Content Background Color"
              >
                <div
                  style={{
                    width: '1.25rem',
                    height: '1.25rem',
                    backgroundColor: contentBackgroundColor,
                    border: '1px solid #ccc',
                    borderRadius: '0.125rem',
                    position: 'relative',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      top: '50%',
                      left: '50%',
                      transform: 'translate(-50%, -50%)',
                      width: '0.75rem',
                      height: '0.75rem',
                      backgroundColor: 'rgba(0,0,0,0.1)',
                      borderRadius: '0.125rem',
                    }}
                  />
                </div>
                <DownOutlined rotate={openContentBackgroundPicker ? 180 : 0} />
              </div>
            </ColorPicker>
            <ConfigProvider
              theme={{
                components: {
                  Select: {
                    /* here is your component tokens */
                    selectorBg: theme === 'dark' ? '#2d2e30' : '#ffffff',
                    optionSelectedBg: theme === 'dark' ? '#444646' : '#1ea1eb',
                    hoverBorderColor: theme === 'dark' ? '#444646' : '#1ea1eb',
                  },
                },
                token: {
                  /* here is your global tokens */
                  colorBgElevated: theme === 'dark' ? '#2d2e30' : '#ffffff',
                  colorText: theme === 'dark' ? '#ffffff' : '#2d2e30',
                },
              }}
            >
              <Select
                value={editor.getAttributes('textStyle').fontSize || ''}
                style={{ width: '6rem', height: '2rem', alignSelf: 'center' }}
                onChange={(value) => {
                  editor
                    .chain()
                    .focus()
                    .setMark('textStyle', { fontSize: value })
                    .run();
                }}
                options={[
                  { value: '', label: t('Size') },
                  { value: '12px', label: '12px' },
                  { value: '14px', label: '14px' },
                  { value: '16px', label: '16px' },
                  { value: '18px', label: '18px' },
                  { value: '20px', label: '20px' },
                  { value: '24px', label: '24px' },
                  { value: '28px', label: '28px' },
                ]}
              />
            </ConfigProvider>
          </div>

          <div className="toolbar-divider"></div>

          <div className="toolbar-group">
            <button
              onClick={() => editor.chain().focus().setTextAlign('left').run()}
              className={
                editor.isActive({ textAlign: 'left' }) ? 'is-active' : ''
              }
              title="Align Left"
              type="button"
            >
              <FaAlignLeft />
            </button>
            <button
              onClick={() =>
                editor.chain().focus().setTextAlign('center').run()
              }
              className={
                editor.isActive({ textAlign: 'center' }) ? 'is-active' : ''
              }
              title="Align Center"
              type="button"
            >
              <FaAlignCenter />
            </button>
            <button
              onClick={() => editor.chain().focus().setTextAlign('right').run()}
              className={
                editor.isActive({ textAlign: 'right' }) ? 'is-active' : ''
              }
              title="Align Right"
              type="button"
            >
              <FaAlignRight />
            </button>
            <button
              className={
                editor.isActive('heading', { level: 1 }) ? 'is-active' : ''
              }
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 1 }).run()
              }
              title="Heading 1"
              type="button"
            >
              <TbH1 className="heading-icon-h1" />
            </button>
            <button
              className={
                editor.isActive('heading', { level: 2 }) ? 'is-active' : ''
              }
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 2 }).run()
              }
              title="Heading 2"
              type="button"
            >
              <TbH2 className="heading-icon-h2" />
            </button>
            <button
              className={
                editor.isActive('heading', { level: 3 }) ? 'is-active' : ''
              }
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 3 }).run()
              }
              title="Heading 3"
              type="button"
            >
              <TbH3 className="heading-icon-h3" />
            </button>
            <button
              className={
                editor.isActive('heading', { level: 4 }) ? 'is-active' : ''
              }
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 4 }).run()
              }
              title="Heading 4"
              type="button"
            >
              <TbH4 className="heading-icon-h4" />
            </button>
            <button
              className={
                editor.isActive('heading', { level: 5 }) ? 'is-active' : ''
              }
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 5 }).run()
              }
              title="Heading 5"
              type="button"
            >
              <TbH5 className="heading-icon-h5" />
            </button>
            <button
              className={
                editor.isActive('heading', { level: 6 }) ? 'is-active' : ''
              }
              onClick={() =>
                editor.chain().focus().toggleHeading({ level: 6 }).run()
              }
              title="Heading 6"
              type="button"
            >
              <TbH6 className="heading-icon-h6" />
            </button>
          </div>

          <div className="toolbar-divider"></div>

          <div className="toolbar-group">
            <button
              className={editor.isActive('bulletList') ? 'is-active' : ''}
              onClick={() => editor.chain().focus().toggleBulletList().run()}
              title="Bullet List"
              type="button"
            >
              <FaListUl />
            </button>
            <button
              className={editor.isActive('orderedList') ? 'is-active' : ''}
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
              title="Ordered List"
              type="button"
            >
              <FaListOl />
            </button>

            <button
              onClick={handlePrint}
              title="Print Preview"
              type="button"
            >
              <FaPrint />
            </button>
          </div>

          <div className="toolbar-divider"></div>

          <div className="toolbar-group">
            <button
              className={editor.isActive('code') ? 'is-active' : ''}
              onClick={() => editor.chain().focus().toggleCode().run()}
              title="Inline Code"
              type="button"
            >
              <FaCode />
            </button>
            <button
              className={editor.isActive('codeBlock') ? 'is-active' : ''}
              onClick={() => editor.chain().focus().toggleCodeBlock().run()}
              title="Code Block"
              type="button"
            >
              <BsCodeSquare />
            </button>
          </div>

          <div className="toolbar-divider"></div>

          <div className="toolbar-group">
            <button
              onClick={() => editor.chain().focus().setHorizontalRule().run()}
              title="Horizontal Rule"
              type="button"
            >
              <FaRulerHorizontal />
            </button>
            <button
              onClick={() => editor.chain().focus().setHardBreak().run()}
              title="Line Break"
              type="button"
            >
              <BsFileBreak />
            </button>
            <button
              onClick={addImage}
              title="Insert Image"
              type="button"
            >
              <FaImage />
            </button>
          </div>

          {/* <div className="toolbar-divider"></div> */}

          <div className="toolbar-group">
            <button
              onClick={() => editor.chain().focus().undo().run()}
              disabled={!editor.can().undo()}
              title="Undo"
              type="button"
            >
              <FaUndo />
            </button>
            <button
              onClick={() => editor.chain().focus().redo().run()}
              disabled={!editor.can().redo()}
              title="Redo"
              type="button"
            >
              <FaRedo />
            </button>
          </div>

          <div className="toolbar-divider"></div>

          <div className="toolbar-group">
            <button
              type="button"
              onClick={() =>
                editor
                  .chain()
                  .focus()
                  .insertTable({ rows: 3, cols: 3, withHeaderRow: false })
                  .run()
              }
              title="Insert Table"
            >
              <FaTable />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().deleteTable().run()}
              disabled={!editor.can().deleteTable()}
              title="Delete Table"
            >
              <BsTrash />
            </button>
            <button
              type="button"
              onClick={toggleTableBorders}
              title="Toggle Table Borders"
              className={isTableBorderVisible ? 'is-active' : ''}
            >
              <FaBorderNone />
            </button>
            <button
              type="button"
              onClick={toggleRowHeader}
              disabled={!editor.isActive('table')}
              className={isRowHeaderActive ? 'is-active' : ''}
              title="Toggle Row as Header"
            >
              <MdOutlineViewHeadline />
            </button>

            <div className="toolbar-divider"></div>

            <button
              type="button"
              onClick={() => editor.chain().focus().addColumnBefore().run()}
              disabled={!editor.can().addColumnBefore()}
              title="Add Column Before"
            >
              <MdArrowBack className="table-icon" />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().addColumnAfter().run()}
              disabled={!editor.can().addColumnAfter()}
              title="Add Column After"
            >
              <MdArrowForward className="table-icon" />
            </button>

            <div className="toolbar-divider"></div>

            <button
              type="button"
              onClick={() => editor.chain().focus().addRowBefore().run()}
              disabled={!editor.can().addRowBefore()}
              title="Add Row Before"
            >
              <MdArrowUpward className="table-icon" />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().addRowAfter().run()}
              disabled={!editor.can().addRowAfter()}
              title="Add Row After"
            >
              <MdArrowDownward className="table-icon" />
            </button>

            <div className="toolbar-divider"></div>

            <button
              type="button"
              onClick={() => editor.chain().focus().deleteColumn().run()}
              disabled={!editor.can().deleteColumn()}
              title="Delete Column"
            >
              <MdOutlineDeleteOutline className="table-icon-delete" />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().deleteRow().run()}
              disabled={!editor.can().deleteRow()}
              title="Delete Row"
            >
              <MdOutlineTableRows className="table-icon-delete" />
            </button>

            <div className="toolbar-divider"></div>

            <button
              type="button"
              onClick={() => editor.chain().focus().mergeCells().run()}
              disabled={!editor.can().mergeCells()}
              title="Merge Cells"
            >
              <FaObjectGroup />
            </button>
            <button
              type="button"
              onClick={() => editor.chain().focus().splitCell().run()}
              disabled={!editor.can().splitCell()}
              title="Split Cell"
            >
              <FaObjectUngroup />
            </button>
          </div>
        </div>

        <div className="tiptap-editor">
          <div
            style={{
              backgroundColor: contentBackgroundColor,
              minHeight: '100%',
              padding: '6px',
              borderRadius: '8px',
            }}
          >
            <EditorContent editor={editor} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default CustomTiptap;
