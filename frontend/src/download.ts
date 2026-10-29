/** Save a blob already obtained through the authenticated API. */
export function saveDownloadedFile(blob:Blob,filename:string) {
  const url=URL.createObjectURL(blob),link=document.createElement("a");
  link.href=url;link.download=filename;
  document.body.append(link);link.click();link.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),30000);
}
