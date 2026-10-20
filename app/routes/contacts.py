from fastapi import APIRouter, HTTPException
from typing import List
from app.models import Contact
from app.database import (
    get_all_contacts,
    get_contact_by_id,
    save_contact,
    delete_contact
)

router = APIRouter(prefix="/api/contacts", tags=["Contacts"])

@router.get("", response_model=List[Contact])
async def list_contacts():
    return get_all_contacts()

@router.post("", response_model=Contact)
async def create_contact(contact: Contact):
    return save_contact(contact)

@router.put("/{contact_id}", response_model=Contact)
async def update_contact(contact_id: str, contact: Contact):
    existing = get_contact_by_id(contact_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact.id = contact_id
    return save_contact(contact)

@router.delete("/{contact_id}")
async def remove_contact(contact_id: str):
    success = delete_contact(contact_id)
    if not success:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"message": "Contact deleted successfully"}
