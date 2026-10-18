/**
 * Editor de texto enriquecido (WYSIWYG) de la revisión: encabezados, negritas, cursivas, listas, citas y enlaces.
 * Se carga solo al editar (React.lazy), para que el resto de la plataforma no descargue el editor.
 */
import { useId } from 'react';
import { EditorContent, useEditor, type Editor } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';

interface Props {
  label: string;
  initialHtml: string;
  onChange: (html: string) => void;
}

interface ToolProps {
  editor: Editor;
  label: string;
  text: string;
  active: boolean;
  onClick: () => void;
}

function Tool({ label, text, active, onClick }: ToolProps) {
  return (
    <button type="button" className={active ? 'rte__tool rte__tool--active' : 'rte__tool'} aria-label={label} title={label} aria-pressed={active} onMouseDown={(e) => e.preventDefault()} onClick={onClick}>
      {text}
    </button>
  );
}

export default function RichTextEditor({ label, initialHtml, onChange }: Props) {
  const labelId = useId();
  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        heading: { levels: [1, 2, 3] },
        code: false,
        codeBlock: false,
        horizontalRule: false,
        link: { openOnClick: false, autolink: true, protocols: ['http', 'https', 'mailto'], defaultProtocol: 'https' },
      }),
    ],
    content: initialHtml,
    shouldRerenderOnTransaction: true,
    editorProps: { attributes: { class: 'rte__content prose', 'aria-labelledby': labelId, 'aria-multiline': 'true', role: 'textbox' } },
    onUpdate: ({ editor: current }) => onChange(current.getHTML()),
  });

  if (!editor) return null;
  const chain = () => editor.chain().focus();
  const setLink = () => {
    const previous = (editor.getAttributes('link').href as string | undefined) ?? 'https://';
    const url = window.prompt('Dirección del enlace (déjala vacía para quitarlo):', previous);
    if (url === null) return;
    if (!url.trim() || url.trim() === 'https://') chain().extendMarkRange('link').unsetLink().run();
    else chain().extendMarkRange('link').setLink({ href: url.trim() }).run();
  };

  return (
    <div className="rte">
      <span className="field__label" id={labelId}>
        {label}
      </span>
      <div className="rte__toolbar" role="toolbar" aria-label="Formato del texto">
        <Tool editor={editor} label="Título 1" text="H1" active={editor.isActive('heading', { level: 1 })} onClick={() => chain().toggleHeading({ level: 1 }).run()} />
        <Tool editor={editor} label="Título 2" text="H2" active={editor.isActive('heading', { level: 2 })} onClick={() => chain().toggleHeading({ level: 2 }).run()} />
        <Tool editor={editor} label="Título 3" text="H3" active={editor.isActive('heading', { level: 3 })} onClick={() => chain().toggleHeading({ level: 3 }).run()} />
        <span className="rte__sep" aria-hidden="true" />
        <Tool editor={editor} label="Negrita" text="B" active={editor.isActive('bold')} onClick={() => chain().toggleBold().run()} />
        <Tool editor={editor} label="Cursiva" text="I" active={editor.isActive('italic')} onClick={() => chain().toggleItalic().run()} />
        <Tool editor={editor} label="Subrayado" text="U" active={editor.isActive('underline')} onClick={() => chain().toggleUnderline().run()} />
        <Tool editor={editor} label="Tachado" text="S" active={editor.isActive('strike')} onClick={() => chain().toggleStrike().run()} />
        <span className="rte__sep" aria-hidden="true" />
        <Tool editor={editor} label="Lista con viñetas" text="• Lista" active={editor.isActive('bulletList')} onClick={() => chain().toggleBulletList().run()} />
        <Tool editor={editor} label="Lista numerada" text="1. Lista" active={editor.isActive('orderedList')} onClick={() => chain().toggleOrderedList().run()} />
        <Tool editor={editor} label="Cita" text="« Cita »" active={editor.isActive('blockquote')} onClick={() => chain().toggleBlockquote().run()} />
        <Tool editor={editor} label="Enlace" text="Enlace" active={editor.isActive('link')} onClick={setLink} />
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
