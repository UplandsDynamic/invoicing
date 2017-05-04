========================
**Aninstance Invoicing**
========================

----------------
**Demo Details**
----------------

This is the code for a working demo of the Aninstance Invoicing application, as running here:

https://invoicing.aninstance.com

The application is intended to be distributed and deployed using Docker.

Please get in touch with questions or feedback, which are both very welcome.

Note that this code is as used for the demo at invoicing.aninstance.com. It is configured for that purpose and is
made available here for reference only. The code is based on my 'Aninstance Framework', which allows for the integration of 
modules (or 'apps'), providing additional functionality, in order to to build out a fully fledged website. 
The settings.py and various other files would clearly need to be configured to suit a new install.

It is assumed a reverse proxy would be set up to forward requests to the docker container. Such setup is not covered here.

Features of this app are described in the usage instructions below.

Note that the design of the user interface (colours, layout, etc) is fully customisable. What's here is for demonstration purposes only.

Supported, hosted instances may be available for purchase soon (priced per month) if there is sufficient interest.

Please note that the app's email functionality has been disabled in this demo.

-----------
**Contact**
-----------

Developer contact: https://www.aninstance.com/contact

------------
**Features**
------------

Features include:

- Define a primary and secondary business accounts
- Define client accounts
- Define invoice items
- Define tax rates for individual invoice items
- Define tax status for individual invoices
- Define discounts for individual invoices
- Create recurring invoices
- Auto-updating invoice statues: Draft, Issued, Sent, Overdue, Paid partially, Paid in full, Cancelled
- Automatic generation of itemised bill totals (inc. tax & discounts)
- Automatic generation of PDF of invoice and reciepts
- Optional automatic emailing of PDF invoice/receipts to clients
- Fully customisable email templates
- Fully customisable PDF templates
- Fully customisable interface design (template & CSS)

--------------
**Quickstart**
--------------

The arrows (>) indicate tapping the button with the following title (that should appear prominently on the page).

- Create business profile: "Menu" > "Create new account"

- Create client account: "Menu" > "Create new account"

- Create invoice items: "Menu" > "View invoice items" > "Create new item"

- Create new invoice: "Menu" > "View client accounts" > "Create invoice for [COMPANY NAME]"

- Edit invoice: "Menu" > "View client accounts" > "View invoices for this account" > "Edit this invoice"
