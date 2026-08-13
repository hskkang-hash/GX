import { DownOutlined } from '@ant-design/icons';
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
import { ColorPicker, ConfigProvider, Select, theme as antdTheme } from 'antd';
import React, { useEffect, useRef, useState } from 'react';
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
import { HiTableCells } from 'react-icons/hi2';
import {
  MdArrowBack,
  MdArrowDownward,
  MdArrowForward,
  MdArrowUpward,
  MdFormatColorText,
  MdOutlineDeleteOutline,
  MdOutlineTableRows,
} from 'react-icons/md';
import { TbH1, TbH2, TbH3, TbH4, TbH5, TbH6 } from 'react-icons/tb';
import { useReactToPrint } from 'react-to-print';
import { useTheme } from 'rj-core';
import ImageResize from 'tiptap-extension-resize-image';

import '../assets/style/customTipTap.scss';
import { FontSize } from '../hooks/FontSize';
import {
  replaceQRParagraphWithDiv,
  reverseFormatHTML,
} from '../hooks/convertFields';
import { CustomTiptapProps } from '../type';
import NunjucksRenderer from './NunjucksRenderer';

export const CustomTiptap: React.FC<CustomTiptapProps> = ({
  content = '',
  onChange,
  label,
  heightContent = '500px',
  includeStyles = false,
  fieldsTemplate,
  dataExample,
}) => {
  const [theme] = useTheme();
  const [openFontColorPicker, setOpenFontColorPicker] = useState(false);
  const [openBackgroundPicker, setOpenBackgroundPicker] = useState(false);
  const [isTableBorderVisible, setIsTableBorderVisible] = useState(true);
  const [isRowHeaderActive, setIsRowHeaderActive] = useState(false);
  const [localContent, setLocalContent] = useState(content);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const printRef = useRef<HTMLDivElement>(null);

  const handlePrint = useReactToPrint({
    contentRef: printRef,
    documentTitle: 'TipTap Content',
  });

  const contentStyles = `
  /* Headings */
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
    background-color: ${theme === 'dark' ? '#343a40' : '#f8f9fa'};
    border-radius: 4px;
    color: ${theme === 'dark' ? '#e9ecef' : '#212529'};
    font-size: 0.85rem;
    font-family: 'JetBrainsMono', monospace;
    padding: 0.25em 0.3em;
  }

  .tiptap-preview pre {
    background: ${theme === 'dark' ? '#343a40' : '#f8f9fa'};
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
  

  .hide-table-borders table tbody td{
     border: none;
  }
`;

  const editor = useEditor({
    content,
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
    ],
    onUpdate({ editor }) {
      if (onChange) {
        let editorHTML = `<div class="tiptap-preview ${isTableBorderVisible ? '' : 'hide-table-borders'
          }">${editor.getHTML()}</div>`;

        editorHTML = editorHTML.replace(
          /<img([^>]*)>/g,
          '<div class="image-wrapper"><img$1></div>',
        );

        if (includeStyles) {
          editorHTML = `<style>${contentStyles}</style>${editorHTML}`;
        }
        setLocalContent(editorHTML);
        onChange(editorHTML);
      }
    },
    onSelectionUpdate({ editor }) {
      // Check if the current selection is in a header row
      const isHeader = editor.isActive('tableHeader');
      setIsRowHeaderActive(isHeader);
    },
  });

  useEffect(() => {
    if (editor && content !== localContent) {
      const cleanContent = reverseFormatHTML(content);

      const { from, to } = editor.state.selection;
      editor.commands.setContent(cleanContent, false);
      editor.commands.setTextSelection({ from, to });
      setLocalContent(content);

      // check div has class hide-table-borders setIsTableBorderVisible to true
      const divElement = document.querySelector('.hide-table-borders');
      if (divElement) {
        setIsTableBorderVisible(true);
        toggleTableBorders();
      } else {
        setIsTableBorderVisible(false);
      }
    }
  }, [content, editor, includeStyles, localContent]);

  const toggleTableBorders = () => {
    const editorElement = document.querySelector('.tiptap-editor');
    // get table element
    const tableElement = editorElement?.querySelector('table');
    if (tableElement) {
      if (isTableBorderVisible) {
        tableElement.classList.add('hide-table-borders');
      } else {
        tableElement.classList.remove('hide-table-borders');
      }
      setIsTableBorderVisible(!isTableBorderVisible);

      // Manually call onChange with updated content
      if (onChange && editor) {
        let html = `<div class="tiptap-preview ${isTableBorderVisible ? 'hide-table-borders' : ''
          }">${editor.getHTML()}</div>`;

        if (includeStyles) {
          html = `<style>${contentStyles}</style>${html}`;
        }
        setLocalContent(html);
        onChange(html);
      }
    }
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

  const handleTemplateWheelScroll = (
    event: React.WheelEvent<HTMLDivElement>,
  ): void => {
    event.preventDefault();
    const container = event.currentTarget;
    container.scrollLeft += event.deltaY;
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
            <ConfigProvider
              theme={{
                algorithm:
                  theme === 'dark'
                    ? antdTheme.darkAlgorithm
                    : antdTheme.defaultAlgorithm,
              }}
            >
              <Select
                value={editor.getAttributes('textStyle').fontSize || ''}
                style={{
                  width: '6rem', height: '2rem', alignSelf: 'center',
                  color: theme == "dark" ? '#ffffff' : '#000000',
                }}

                onChange={(value) => {
                  editor
                    .chain()
                    .focus()
                    .setMark('textStyle', { fontSize: value })
                    .run();
                }}
                optionRender={(option) => (
                  <span
                    style={{
                      color: theme == "dark" ? '#ffffff' : '#000000',
                      fontSize: '14px',
                    }}
                  >
                    {option.label}
                  </span>
                )}
                options={[
                  { value: '', label: 'Size' },
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
              className={!isTableBorderVisible ? 'is-active' : ''}
              title="Toggle Table Borders"
            >
              <FaBorderNone />
            </button>
            <button
              onClick={() => editor.chain().focus().toggleHeaderCell().run()}
              disabled={!editor.can().toggleHeaderCell()}
              className={isRowHeaderActive ? 'is-active' : ''}
              type="button"
              title="Toggle Header Cell"
            >
              <HiTableCells />
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
          {fieldsTemplate && fieldsTemplate.length > 0 && (
            <div
              className="toolbar-template"
              onWheel={handleTemplateWheelScroll}
            >
              {fieldsTemplate.map((field, index) => (
                <button
                  key={`${field.value}-${index}`}
                  onClick={() =>
                    editor.chain().focus().insertContent(field.value).run()
                  }
                  type="button"
                >
                  {field.label}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="tiptap-editor">
          <EditorContent editor={editor} />
        </div>

        {/* Hidden printable content */}
        <div style={{ display: 'none' }}>
          <NunjucksRenderer
            printRef={printRef}
            template={replaceQRParagraphWithDiv(localContent)}
            data={dataExample}
          />
        </div>
      </div>
    </div>
  );
};

export default CustomTiptap;
